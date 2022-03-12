try:
    import logging
    import logging.config
    import os
    import sys
    import time

    import requests
    import telegram
    from dotenv import load_dotenv

    import my_ex
except ImportError as error:
    logging.error(f'Ошибка при импорте {error}')

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
    except Exception as error:
        logger.exception('Ошибка при отправке сообщения')
        raise my_ex.MessageSendError from error
    else:
        logger.info('Сообщение отправлено!')


def get_api_answer(current_timestamp):
    """Делает запрос к API и проверяет на ошибки."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.exception('Проблема с доступом к эндпоинту')
        raise my_ex.ErrorWithEndpoint from error
    else:
        if response.status_code != 200:
            logger.error('Код ответа не 200')
            raise my_ex.NotOKError(response.status_code)
        return response.json()


def check_response(response):
    """Проверяет ответ на ошибки."""
    if type(response['homeworks']) is not list:
        logger.error('В ключе "homeworks" не лист')
        raise my_ex.HomeworkNotList
    if 'homeworks' not in response:
        logger.error('"homeworks" не лист')
        raise my_ex.HomeworksNotInResponse
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Получает статус домашки и возвращает сообщение для бота."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет необходимые токены."""
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    return all(tokens)


def send_error(error, bot):
    """Отправяляет ошибки в телеграм."""
    message = f'Сбой в работе программы: {error}'
    send_message(bot, message)


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
    else:
        logger.critical('Отсутствует обязательная переменная окружения')
        sys.exit()

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
