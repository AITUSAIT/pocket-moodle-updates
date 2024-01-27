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

            return {str(_[0]): CourseContent(
                id=_[0],
                name=_[1],
                section=_[2],
                modules=(await cls.get_course_content_modules(course_id, _[0])),
            ) for _ in contents}

    @classmethod
    async def insert_course_content(
        cls, course_id: int, name: str, section: int, content_id: int
    ) -> int:
        async with cls.pool.acquire() as connection:
            content_id = await connection.fetchval(
                '''
                INSERT INTO courses_contents (id, name, section, course_id)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
                ''',
                content_id, name, section, course_id
            )
            return content_id

    @classmethod
    async def if_course_content_exist(cls, content_id: int) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents WHERE id = $1',
                content_id
            )
            return count > 0

    @classmethod
    async def update_course_content(
        cls, content_id: int, name: str, section: int
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                UPDATE courses_contents
                SET name = $1, section = $2
                WHERE id = $3;
                ''',
                name, section, content_id
            )

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

            return {str(_[0]): CourseContentModule(
                id=_[0],
                url=_[1],
                name=_[2],
                modplural=_[3],
                modname=_[4],
                files=(await cls.get_course_content_module_files(content_id, _[0])),
                urls=(await cls.get_course_content_module_urls(content_id, _[0])),
            ) for _ in modules}

    @classmethod
    async def if_course_content_module_exist(cls, module_id: int) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules WHERE id = $1',
                module_id
            )
            return count > 0

    @classmethod
    async def insert_course_content_module(
        cls, module_id: int, content_id: int, url: str, name: str, modplural: str, modname: str
    ) -> int:
        async with cls.pool.acquire() as connection:
            module_id = await connection.fetchval(
                '''
                INSERT INTO courses_contents_modules (id, url, name, modplural, modname, courses_contents_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id;
                ''',
                module_id, url, name, modplural, modname, content_id
            )
            return module_id

    @classmethod
    async def update_course_content_module(
        cls, module_id: int, url: str, name: str, modplural: str, modname: str
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                UPDATE courses_contents_modules
                SET url = $1, name = $2, modplural = $3, modname = $4
                WHERE id = $5;
                ''',
                url, name, modplural, modname, module_id
            )

    @classmethod
    async def get_course_content_module_files(cls, module_id: int) -> dict[str, CourseContentModuleFile]:
        async with cls.pool.acquire() as connection:
            files = await connection.fetch(f'''
            SELECT
                f.id, f.filename, f.filesize, f.fileurl, f.timecreated, f.timemodified, f.mimetype, f.bytes
            FROM
                courses_contents_modules_files f
            WHERE
                f.courses_contents_modules_id = $1;
            ''', module_id)

            return {str(_[3]): CourseContentModuleFile(
                id=_[0],
                filename=_[1],
                filesize=_[2],
                fileurl=_[3],
                timecreated=_[4],
                timemodified=_[5],
                mimetype=_[6],
                bytes=_[7],
            ) for _ in files}

    @classmethod
    async def if_course_content_module_file_exist(cls, fileurl: str) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules_files WHERE fileurl = $1',
                fileurl
            )
            return count > 0

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
    async def update_course_content_module_file(
        cls, module_id: int, filename: str, filesize: int, fileurl: str,
        timecreated: int, timemodified: int, mimetype: str, bytes: bytes
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                UPDATE courses_contents_modules_files
                SET filename = $1, filesize = $2, fileurl = $3, timecreated = $4, timemodified = $5, mimetype = $6, bytes = $7
                WHERE fileurl = $3 and courses_contents_modules_id = $8
                ''',
                filename, filesize, fileurl, timecreated, timemodified, mimetype, bytes, module_id
            )

    @classmethod
    async def get_course_content_module_urls(cls, module_id: int) -> dict[str, CourseContentModuleUrl]:
        async with cls.pool.acquire() as connection:
            urls = await connection.fetch('''
            SELECT
                u.id, u.name, u.url
            FROM
                courses_contents_modules_urls u
            WHERE
                u.courses_contents_modules_id = $1;
            ''', module_id)

            return {str(_[1]): CourseContentModuleUrl(
                id=_[0],
                name=_[1],
                url=_[2],
            ) for _ in urls}

    @classmethod
    async def if_course_content_module_url_exist(cls, url: str) -> bool:
        async with cls.pool.acquire() as connection:
            count = await connection.fetchval(
                'SELECT COUNT(*) FROM courses_contents_modules_urls WHERE url = $1',
                url
            )
            return count > 0

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
    async def update_course_content_module_url(
        cls, module_id: int, name: str, url: str
    ):
        async with cls.pool.acquire() as connection:
            await connection.execute(
                '''
                UPDATE courses_contents_modules_urls
                SET name = $1
                WHERE url = $2 and courses_contents_modules_id = $3;
                ''',
                name, url, module_id
            )
