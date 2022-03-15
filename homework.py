import logging
import logging.config
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

import my_ex

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Посылает сообщение в телеграм."""
    logger.info('Сообщение отправляется')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info('Сообщение отправлено!')
    except Exception as error:
        logger.exception('Ошибка при отправке сообщения')
        raise my_ex.MessageSendError from error


def get_api_answer(current_timestamp):
    """Делает запрос к API и проверяет на ошибки."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error('Код ответа не 200')
            raise my_ex.NotOKError(response.status_code)
    except Exception as error:
        logger.exception('Проблема с доступом к эндпоинту')
        raise my_ex.ErrorWithEndpoint from error

    try:
        return response.json()
    except Exception as error:
        logger.exception('Ответ не в формате json')
        raise my_ex.ResponseNotJSON from error


def check_response(response):
    """Проверяет ответ на ошибки."""
    if not isinstance(response['homeworks'], list):
        logger.error('В ключе homeworks не лист')
        raise my_ex.HomeworkNotList
    if 'homeworks' not in response:
        logger.error('homeworks отсутствует в ответе')
        raise my_ex.HomeworksNotInResponse
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Получает статус домашки и возвращает сообщение для бота."""
    HOMEWORK_KEYS = (
        'homework_name',
        'status'
    )
    for key in HOMEWORK_KEYS:
        if key not in homework:
            logger.error(f'Нет ожидаемого ключа: {key}')
            raise KeyError

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_STATUSES:
        logger.error('В ответе обнаружен недокументированный статус')
        raise my_ex.UndocumentedStatus
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет необходимые токены."""
    TOKENS = (
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    )
    return all(TOKENS)


def send_error(error, bot):
    """Отправяляет ошибки в телеграм."""
    message = f'Сбой в работе программы: {error}'
    send_message(bot, message)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная окружения')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    current_report = {'homework_name': 'current_status'}
    prev_report = {'homework_name': 'status'}

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.info('Вашу работа еще не взяли на проверку(')
            else:
                homework = homeworks[0]
                current_status = parse_status(homework)
                current_report.update(dict(
                    homework_name=homework.get('homework_name'),
                    current_status=current_status
                ))
                if current_report != prev_report:
                    send_message(bot, current_status)
                    prev_report = current_report.copy()
                else:
                    logger.debug('В ответе отсутсвуют новые статусы')
            current_timestamp = int(time.time())
        except Exception as error:
            send_error(error, bot)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    ERROR_LOG_FILENAME = '.program.log'

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': ('%(asctime)s : %(levelname)s : '
                           '%(message)s : %(lineno)s')
            },
        },
        'handlers': {
            'logfile': {
                'formatter': 'default',
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': ERROR_LOG_FILENAME,
                'backupCount': 5,
                'maxBytes': 50000000,
            },
            'verbose_output': {
                'formatter': 'default',
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'root': {
                'handlers': ['logfile'],
                'level': 'DEBUG',
            },
            '__main__': {
                'handlers': ['verbose_output'],
                'level': 'INFO',
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    main()
