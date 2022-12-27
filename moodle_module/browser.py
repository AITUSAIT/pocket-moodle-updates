import logging
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import \
    visibility_of_element_located as voel
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

from config import chrome_options
from functions.logger import logger


class Browser:
    def __init__(self, proxy: str) -> None:
        logging.getLogger('seleniumwire').setLevel(logging.ERROR)
        self.set_options()
        options = {
            'proxy': {
                'http': proxy,
            }
        }
        self.driver = webdriver.Chrome(options=self.chrome_options, seleniumwire_options=options)
        self.wait = WebDriverWait(self.driver, 5)

    def set_options(self):
        self.chrome_options = Options()
        for option in chrome_options:
            self.chrome_options.add_argument(option)

    async def get_cookies_moodle(self, user_id, BARCODE, PASSWD) -> tuple[dict, bool, str, str]:
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
                    return {}, False, 'Invalid Login (barcode)', None
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
                        return {}, False, 'Invalid Login (passwd)', None
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
            try:
                token = self.get_token_du()
            except:
                token = None
            self.driver.close()
            self.driver.quit()
            return cookies, True, '', token
        except:
            logger.error(user_id, exc_info=True)
            try:
                self.driver.close()
                self.driver.quit()
            except:
                ...
            return {}, False, -1, None

    def get_cookies_data(self):
        cookies = {}
        session_cookies = self.driver.get_cookies()
        for cookie in session_cookies:
            cookies[cookie['name']] = cookie['value']
        return cookies

    def get_token_du(self):
        url = "https://login.microsoftonline.com/158f15f3-83e0-4906-824c-69bdc50d9d61/oauth2/v2.0/authorize?client_id=9f15860b-4243-4610-845e-428dc4ae43a8&response_type=code&redirect_uri=https%3A%2F%2Fdu.astanait.edu.kz%2Flogin&response_mode=query&scope=offline_access%20user.read%20mail.read&state=12345"
        self.driver.get(url)
        self.wait.until(voel((
            By.XPATH,
            '//*[@id="root"]/section/section/header/div/div[3]/div/div/a/span[1]'
        )))
        
        return self.ls_get('token')
    
    def ls_items(self) :
        return self.driver.execute_script( \
            "var ls = window.localStorage, items = {}; " \
            "for (var i = 0, k; i < ls.length; ++i) " \
            "  items[k = ls.key(i)] = ls.getItem(k); " \
            "return items; ")

    def ls_keys(self) :
        return self.driver.execute_script( \
            "var ls = window.localStorage, keys = []; " \
            "for (var i = 0; i < ls.length; ++i) " \
            "  keys[i] = ls.key(i); " \
            "return keys; ")

    def ls_get(self, key):
        return self.driver.execute_script("return window.localStorage.getItem(arguments[0]);", key)

    def ls_set(self, key, value):
        self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)

    def ls_has(self, key):
        return key in self.keys()

    def ls_remove(self, key):
        self.driver.execute_script("window.localStorage.removeItem(arguments[0]);", key)

    def ls_clear(self):
        self.driver.execute_script("window.localStorage.clear();")

    