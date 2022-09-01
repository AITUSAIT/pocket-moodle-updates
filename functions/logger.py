import logging


logging.basicConfig(filename="logs.log",
                    filemode="w",
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    datefmt='%d/%m %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()