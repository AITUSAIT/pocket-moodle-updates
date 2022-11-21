import json
from asyncio import sleep

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import \
    visibility_of_element_located as voel, invisibility_of_element_located as ioel, invisibility_of_element as ioe
from selenium.webdriver.support.ui import WebDriverWait

from config import chrome_options
from functions import aioredis
from functions.bot import send
from functions.logger import logger


class Browser:
    def __init__(self) -> None:
        self.set_options()
        self.driver = Chrome(options=self.chrome_options)
        self.wait = WebDriverWait(self.driver, 5)

    def set_options(self):
        self.chrome_options = Options()
        for option in chrome_options:
            self.chrome_options.add_argument(option)

    async def get_cookies_moodle(self, user_id, BARCODE, PASSWD):
        try:
            url = "https://moodle.astanait.edu.kz/auth/oidc/"
            self.driver.get(url)

            self.wait.until(voel((
                By.XPATH,
                '//*[@id="i0116"]'
            ))).send_keys(BARCODE+"@astanait.edu.kz")
            self.wait.until(voel((
                By.XPATH,
                '//*[@id="idSIButton9"]'
            ))).click()


            try:
                self.wait.until(voel((
                    By.XPATH,
                    '//*[@id="i0118"]'
                ))).send_keys(PASSWD)
            except:
                usernameError = self.driver.find_element(By.XPATH, '//*[@id="usernameError"]')
                if usernameError.is_displayed():
                    self.driver.close()
                    self.driver.quit()
                    return {}, False, 'Invalid Login (barcode)'
            else:
                self.wait.until(voel((
                    By.XPATH,
                    '//*[@id="idSIButton9"]'
                ))).click()


            try:
                self.wait.until(voel((
                    By.XPATH,
                    '//*[@id="lightbox"]/div[3]/div/div[2]/div/div[3]/div[1]/div/label/span'
                )))
            except:
                try:
                    passwordError = self.driver.find_element(By.XPATH, '//*[@id="passwordError"]')
                    if passwordError.is_displayed():
                        self.driver.close()
                        self.driver.quit()
                        return {}, False, 'Invalid Login (passwd)'
                except:
                    self.driver.find_element(By.XPATH, '//*[@id="idSubmit_ProofUp_Redirect"]').click()
                    self.wait.until(voel((
                        By.XPATH,
                        '//*[@id="CancelLinkButton"]'
                    ))).click()
            self.wait.until(voel((
                By.XPATH,
                '//*[@id="idSIButton9"]'
            ))).click()
            
            self.wait.until(voel((
                By.XPATH,
                '//*[@id="action-menu-toggle-1"]/span/span[2]/span/img'
            )))

            cookies = self.get_cookies_data()
            await self.login_and_get_gpa(user_id)
            self.driver.close()
            self.driver.quit()
            return cookies, True, ''
        except:
            logger.error(user_id, exc_info=True)
            try:
                self.driver.close()
                self.driver.quit()
            except:
                ...
            return {}, False, -1

    def get_cookies_data(self):
        cookies = {}
        session_cookies = self.driver.get_cookies()
        for cookie in session_cookies:
            cookies[cookie['name']] = cookie['value']
        return cookies

    def get_soup(self):
        url = "https://login.microsoftonline.com/158f15f3-83e0-4906-824c-69bdc50d9d61/oauth2/v2.0/authorize?client_id=9f15860b-4243-4610-845e-428dc4ae43a8&response_type=code&redirect_uri=https%3A%2F%2Fdu.astanait.edu.kz%2Flogin&response_mode=query&scope=offline_access%20user.read%20mail.read&state=12345"
        self.driver.get(url)
        self.wait.until(voel((
            By.XPATH,
            '//*[@id="root"]/section/section/header/div/div[3]/div/div/a/span[1]'
        )))
        
        self.driver.get('https://du.astanait.edu.kz/transcript')
        self.wait.until(ioel((
            By.XPATH,
            '//span[@class="ant-spin-dot ant-spin-dot-spin"]'
        )))

        soup = self.driver.page_source
        return soup

    def get_total_gpa(self, soup):
        soup = BeautifulSoup(soup, 'html.parser')

        table = soup.find('table')
        text_avg_gpa = table.find('tfoot', {'class': 'ant-table-summary'}).text

        array_gpa = []
        rows = table.find_all('tr')
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) > 0:
                if 'trimester' in str(cells[1].text).lower():
                    array_gpa.append(str(cells[1].text))
        array_gpa.append(text_avg_gpa)

        return array_gpa

    async def login_and_get_gpa(self, user_id):
        try:
            arr_gpa = self.get_total_gpa(self.get_soup())

            gpa_text = "{"
            for item in arr_gpa:
                text, gpa = item.split(' - ')
                gpa_dict = f'"{text}": {gpa},'
                gpa_text += gpa_dict
            gpa_text = gpa_text[:-1] +"}"
            gpa_dict = json.loads(gpa_text)

            data = {}
            data['gpa'] = gpa_dict
                
            await aioredis.set_key(user_id, 'gpa', data['gpa'])
            return 1
        except Exception as exc:
            # logger.error(f"{user_id} {exc}", exc_info=True)
            return -1
    