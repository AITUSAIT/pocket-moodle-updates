from random import shuffle
from modules.logger import Logger
from typing import Any
import aiohttp
from config import IS_PROXY
from modules.database import CourseContentDB, CourseDB, NotificationDB, UserDB
from modules.moodle import Moodle, User


class FileDownloadError(Exception):
    pass


async def get_file(url: str, token: str, proxy_dict: dict[str, Any]) -> bytes:
    proxy = f"http://{proxy_dict['login']}:{proxy_dict['passwd']}@{proxy_dict['ip']}:{proxy_dict['http_port']}" if IS_PROXY else None
    async with aiohttp.ClientSession() as session:
        params = {
            "token": token
        }
        async with session.get(url, params=params, proxy=proxy) as response:
            if response.status == 200 and response.headers.get("Content-Type:") != "application/json;":
                return await response.read()
            else:
                raise FileDownloadError(f"Failed to download file from {url}. Status code: {response.status}")


async def update_course_contents(proxy_dict: dict | None):
    users = await UserDB.get_users()
    shuffle(users)

    updated_courses_ids = []

    for _ in users:
        Logger.info(f"=========== {_.user_id=} ==============")
        if not _.api_token:
            continue
        
        user: User = User(
            user_id=_.user_id,
            api_token=_.api_token,
            register_date=_.register_date,
            sub_end_date=_.sub_end_date,
            mail=_.mail, 
            id=None, 
            courses=(await CourseDB.get_courses(_.user_id)), 
            msg=None
        )
        notifications = await NotificationDB.get_notification_status(user.user_id)
        moodle = Moodle(user, proxy_dict, notifications)
        if not await moodle.check():
            continue
        courses = await moodle.get_courses()
        active_courses_ids: tuple[int] = await moodle.get_active_courses_ids(courses)
        
        for course_id in [ cid for cid in active_courses_ids if cid not in updated_courses_ids ]:
            updated_courses_ids.append(course_id)
            
            contents = None
            try:
                contents = await moodle.course_get_contents(course_id)
            except:
                pass
            else:
                for content in contents:
                    content_id = content["id"]
                    content_name = content["name"]
                    content_section = content["section"]
                    
                    if not await CourseContentDB.if_course_content_exist(content_id):
                        await CourseContentDB.insert_course_content(
                            course_id=course_id,
                            name=content_name,
                            section=content_section,
                        )

                    for module in content.get("modules", []):
                        module_id = module["id"]
                        module_name = module["name"]
                        module_url = module.get("url", None)
                        module_modname = module["modname"]
                        module_modplural = module["modplural"]
                        
                        if not await CourseContentDB.if_course_content_module_exist(module_id):
                            await CourseContentDB.insert_course_content_module(
                                content_id=content_id,
                                url=module_url,
                                name=module_name,
                                modplural=module_modplural,
                                modname=module_modname,
                            )
                        
                        for content_file_or_url in module.get("contents", []):
                            if content_file_or_url["type"] == "file":
                                if "mimetype" not in content_file_or_url:
                                    continue
                                content_file = content_file_or_url
                                content_file_filename = content_file["filename"]
                                content_file_fileurl = content_file["fileurl"]
                                content_file_filesize = content_file["filesize"]
                                content_file_timecreated = content_file["timecreated"]
                                content_file_timemodified = content_file["timemodified"]
                                content_file_mimetype = content_file["mimetype"]

                                if not await CourseContentDB.if_course_content_module_file_exist(content_file_fileurl):
                                    try:
                                        content_file_bytes = await get_file(content_file_fileurl, moodle.user.api_token, proxy_dict)
                                    except:
                                        continue
                                    Logger.info(f"{content_id=} {module_id} {content_file_filename} Downloaded")
                                    await CourseContentDB.insert_course_content_module_file(
                                        module_id=module_id,
                                        filename=content_file_filename,
                                        filesize=content_file_filesize,
                                        fileurl=content_file_fileurl,
                                        timecreated=content_file_timecreated,
                                        timemodified=content_file_timemodified,
                                        mimetype=content_file_mimetype,
                                        bytes=content_file_bytes,
                                    )
                                
                                files = await CourseContentDB.get_course_content_module_files(module_id)
                                file = files.get(content_file_fileurl)
                                if not file:
                                    continue
                                
                                if file.filesize != content_file_filesize:
                                    try:
                                        content_file_bytes = await get_file(content_file_fileurl, moodle.user.api_token, proxy_dict)
                                    except:
                                        continue
                                    Logger.info(f"{content_id=} {module_id} {content_file_filename} Updated")
                                    await CourseContentDB.update_course_content_module_file(
                                        module_id=module_id,
                                        filename=content_file_filename,
                                        filesize=content_file_filesize,
                                        fileurl=content_file_fileurl,
                                        timecreated=content_file_timecreated,
                                        timemodified=content_file_timemodified,
                                        mimetype=content_file_mimetype,
                                        bytes=content_file_bytes,
                                    )
                                
                            elif content_file_or_url["type"] == "url":
                                content_url = content_file_or_url
                                content_url_name = content_url["filename"]
                                content_url_url = content_url["fileurl"]
                                
                                if not await CourseContentDB.if_course_content_module_url_exist(content_url_url):
                                    Logger.info(f"{content_id=} {module_id} {content_url_name} Saved")
                                    await CourseContentDB.insert_course_content_module_url(
                                        module_id=module_id,
                                        name=content_url_name,
                                        url=content_url_url,
                                    )
                                
                                urls = await CourseContentDB.get_course_content_module_urls(module_id)
                                url = urls.get(content_url_url)
                                if not url:
                                    continue
                                
                                if url.name != content_url_name:
                                    Logger.info(f"{content_id=} {module_id} {content_file_filename} Updated")
                                    await CourseContentDB.update_course_content_module_url(
                                        module_id=module_id,
                                        name=content_url_name,
                                        url=content_url_url,
                                    )
                                