import logging

logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('log.txt', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(message)s') # %(name)s - %(levelname)s - 
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)