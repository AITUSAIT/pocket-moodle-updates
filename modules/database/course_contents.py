from modules.database import CourseDB
from .models import CourseContent, CourseContentModule, CourseContentModuleFile, CourseContentModuleUrl


class CourseContentDB(CourseDB):
    @classmethod
    async def get_course_contents(cls, course_id: int) -> dict[str, CourseContent]:
        async with cls.pool.acquire() as connection:
            contents = await connection.fetch(f'''
            SELECT
                cc.id, cc.name, cc.section
            FROM
                courses_contents cc
            WHERE
                cc.course_id = $1;
            ''', course_id)
            
            return { str(_[0]): CourseContent(
                id=_[0],
                name=_[1],
                section=_[2],
                modules=(await cls.get_course_content_modules(course_id, _[0])),
            ) for _ in contents }

    @classmethod
    async def get_course_content_modules(cls, content_id: int) -> dict[str, CourseContentModule]:
        async with cls.pool.acquire() as connection:
            modules = await connection.fetch(f'''
            SELECT
                m.id, m.url, m.name, m.modplural, m.modname
            FROM
                courses_contents_modules m
            WHERE
                m.courses_contents_id = $1;
            ''', content_id)
            
            return { str(_[0]): CourseContentModule(
                id=_[0],
                url=_[1],
                name=_[2],
                modplural=_[3],
                modname=_[4],
                files=(await cls.get_course_content_module_files(content_id, _[0])),
                urls=(await cls.get_course_content_module_urls(content_id, _[0])),
            ) for _ in modules }

    @classmethod
    async def get_course_content_module_files(cls, module_id: int) -> dict[str, CourseContentModuleFile]:
        async with cls.pool.acquire() as connection:
            files = await connection.fetch(f'''
            SELECT
                f.filename, f.filesize, f.fileurl, f.timecreated, f.timemodified, f.mimetype, f.bytes
            FROM
                courses_contents_modules_files f
            WHERE
                f.courses_contents_modules_id = $1;
            ''', module_id)
            
            return { str(_[0]): CourseContentModuleFile(
                filename=_[0],
                filesize=_[1],
                fileurl=_[2],
                timecreated=_[3],
                timemodified=_[4],
                mimetype=_[5],
                bytes=_[6],
            ) for _ in files }

    @classmethod
    async def get_course_content_module_urls(cls, module_id: int) -> dict[str, CourseContentModuleUrl]:
        async with cls.pool.acquire() as connection:
            urls = await connection.fetch(f'''
            SELECT
                u.name, u.url
            FROM
                courses_contents_modules_urls u
            WHERE
                u.courses_contents_modules_id = $1;
            ''', module_id)
            
            return { str(_[0]): CourseContentModuleUrl(
                name=_[0],
                url=_[1],
            ) for _ in urls }

    @classmethod
    async def insert_course_content(
        cls, course_id: int, name: str, section: int
    ) -> int:
        async with cls.pool.acquire() as connection:
            content_id = await connection.fetchval(
                '''
                INSERT INTO courses_contents (name, section, course_id)
                VALUES ($1, $2, $3)
                RETURNING id;
                ''',
                name, section, course_id
            )
            return content_id

    @classmethod
    async def insert_course_content_module(
        cls, content_id: int, url: str, name: str, modplural: str, modname: str
    ) -> int:
        async with cls.pool.acquire() as connection:
            module_id = await connection.fetchval(
                '''
                INSERT INTO courses_contents_modules (url, name, modplural, modname, courses_contents_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id;
                ''',
                url, name, modplural, modname, content_id
            )
            return module_id

    @classmethod
    async def insert_course_content_module_file(
        cls, module_id: int, filename: str, filesize: int, fileurl: str,
        timecreated: int, timemodified: int, mimetype: str, bytes: bytes
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                INSERT INTO courses_contents_modules_files 
                    (filename, filesize, fileurl, timecreated, timemodified, mimetype, bytes, courses_contents_modules_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                ''',
                filename, filesize, fileurl, timecreated, timemodified, mimetype, bytes, module_id
            )

    @classmethod
    async def insert_course_content_module_url(
        cls, module_id: int, name: str, url: str
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                INSERT INTO courses_contents_modules_urls (name, url, courses_contents_modules_id)
                VALUES ($1, $2, $3);
                ''',
                name, url, module_id
            )

    @classmethod
    async def if_course_content_exist(cls, content_id: int) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents WHERE id = $1',
                content_id
            )
            return count > 0

    @classmethod
    async def if_course_content_module_exist(cls, module_id: int) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules WHERE id = $1',
                module_id
            )
            return count > 0

    @classmethod
    async def if_course_content_module_file_exist(cls, fileurl: str) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules_files WHERE fileurl = $1',
                fileurl
            )
            return count > 0

    @classmethod
    async def if_course_content_module_url_exist(cls, url: str) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules_urls WHERE url = $1',
                url
            )
            return count > 0
