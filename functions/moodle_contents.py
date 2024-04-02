from random import shuffle

import aiohttp

from config import IS_PROXY
from modules.database import CourseContentDB, CourseDB, NotificationDB, UserDB
from modules.logger import Logger
from modules.moodle import Moodle, User
from modules.proxy_provider import ProxyProvider


class FileDownloadError(Exception):
    pass


class MoodleContents:
    def __init__(self) -> None:
        self.moodle: Moodle

    async def get_file(
        self,
        url: str,
        token: str,
    ) -> bytes:
        async with aiohttp.ClientSession() as session:
            params = {"token": token}
            async with session.get(
                url, params=params, proxy=ProxyProvider.get_proxy() if IS_PROXY else None
            ) as response:
                if response.status == 200 and response.headers.get("Content-Type:") != "application/json;":
                    return await response.read()
                raise FileDownloadError(f"Failed to download file from {url}. Status code: {response.status}")

    async def update_course_contents(self):
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
                mail=_.mail,
                last_active=_.last_active,
                id=None,
                courses=(await CourseDB.get_courses(_.user_id)),
                msg=None,
            )
            notifications = await NotificationDB.get_notification_status(user.user_id)
            self.moodle = Moodle(user, notifications)
            if not await self.moodle.check():
                continue

            try:
                courses = await self.moodle.get_courses()
            except TimeoutError:
                continue
            active_courses_ids: tuple[int] = await self.moodle.get_active_courses_ids(courses)

            for course_id in [cid for cid in active_courses_ids if cid not in updated_courses_ids]:
                updated_courses_ids.append(course_id)

                contents = None
                try:
                    contents = await self.moodle.course_get_contents(course_id)
                except Exception:
                    continue

                for content in contents:
                    content_id = content["id"]
                    content_name = content["name"]
                    content_section = content["section"]

                    await CourseContentDB.insert_course_content(
                        course_id=course_id,
                        name=content_name,
                        section=content_section,
                        content_id=content_id,
                    )

                    for module in content.get("modules", []):
                        module_id = module["id"]
                        module_name = module["name"]
                        module_url = module.get("url", None)
                        module_modname = module["modname"]
                        module_modplural = module["modplural"]

                        await CourseContentDB.insert_course_content_module(
                            module_id=module_id,
                            content_id=content_id,
                            url=module_url,
                            name=module_name,
                            modplural=module_modplural,
                            modname=module_modname,
                        )

                        await self.update_files_and_urls(module=module, content=content)

    async def update_files_and_urls(self, module, content):
        for content_file_or_url in module.get("contents", []):
            if content_file_or_url["type"] == "file":
                await self.update_file(
                    content_id=content["id"], module_id=module["id"], content_file=content_file_or_url
                )

            elif content_file_or_url["type"] == "url":
                await self.update_url(content_id=content["id"], module_id=module["id"], content_url=content_file_or_url)

    async def update_file(self, content_id, module_id, content_file):
        if "mimetype" not in content_file:
            return

        content_file_filename = content_file["filename"]
        content_file_fileurl = content_file["fileurl"]
        content_file_filesize = content_file["filesize"]
        content_file_timecreated = content_file["timecreated"]
        content_file_timemodified = content_file["timemodified"]
        content_file_mimetype = content_file["mimetype"]

        if not await CourseContentDB.if_course_content_module_file_exist(content_file_fileurl):
            try:
                content_file_bytes = await self.get_file(content_file_fileurl, self.moodle.user.api_token)
            except Exception:
                return

            Logger.info(f"{content_id=} {module_id} {content_file_filename} Downloaded")
            await CourseContentDB.insert_course_content_module_file(
                module_id=module_id,
                filename=content_file_filename,
                filesize=content_file_filesize,
                fileurl=content_file_fileurl,
                timecreated=content_file_timecreated,
                timemodified=content_file_timemodified,
                mimetype=content_file_mimetype,
                file_bytes=content_file_bytes,
            )
            return

        files = await CourseContentDB.get_course_content_module_files(module_id)
        file = files.get(content_file_fileurl)
        if not file or file.filesize == content_file_filesize:
            return

        try:
            content_file_bytes = await self.get_file(content_file_fileurl, self.moodle.user.api_token)
        except Exception:
            return

        Logger.info(f"{content_id=} {module_id} {content_file_filename} Updated")
        await CourseContentDB.update_course_content_module_file(
            module_id=module_id,
            filename=content_file_filename,
            filesize=content_file_filesize,
            fileurl=content_file_fileurl,
            timecreated=content_file_timecreated,
            timemodified=content_file_timemodified,
            mimetype=content_file_mimetype,
            file_bytes=content_file_bytes,
        )

    async def update_url(self, content_id, module_id, content_url):
        content_url_name = content_url["filename"]
        content_url_url = content_url["fileurl"]

        if not await CourseContentDB.if_course_content_module_url_exist(content_url_url):
            Logger.info(f"{content_id=} {module_id} {content_url_name} Saved")
            await CourseContentDB.insert_course_content_module_url(
                module_id=module_id,
                name=content_url_name,
                url=content_url_url,
            )
            return

        urls = await CourseContentDB.get_course_content_module_urls(module_id)
        url = urls.get(content_url_url)
        if not url or url.name == content_url_name:
            return

        Logger.info(f"{content_id=} {module_id} {content_url_name} Updated")
        await CourseContentDB.update_course_content_module_url(
            module_id=module_id,
            name=content_url_name,
            url=content_url_url,
        )
