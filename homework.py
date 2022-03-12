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
    logging.error(f'Ошибка при импорте {error}', exc_info=True)

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
    logger.info('Сообщение отправляется')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except Exception as error:
        raise my_ex.MessageSendError from error
    else:
        logger.info('Сообщение отправлено!')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.exception('Эндпоинт шалит')
        raise my_ex.ErrorWithEndpoint from error
    else:
        if response.status_code != 200:
            raise my_ex.NotOKError(response.status_code)
        return response.json()


def check_response(response):
    if type(response['homeworks']) is not list:
        raise my_ex.HomeworkNotList
    if 'homeworks' not in response:
        raise my_ex.HomeworksNotInList
    else:
        return response.get('homeworks')


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    return all(tokens)


def send_error(error, bot):
    message = f'Сбой в работе программы: {error}'
    send_message(bot, message)
    time.sleep(RETRY_TIME)


def main():
    """Основная логика работы бота."""

    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = 10
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
        except my_ex.ErrorWithEndpoint as error:
            logger.exception('Проблема с доступом к эндпоинту')
            send_error(error, bot)
            raise
        except my_ex.HomeworksNotInList as error:
            logger.exception('"homeworks" отсутствует')
            send_error(error, bot)
            raise
        except my_ex.HomeworkNotList as error:
            logger.exception('Под ключом "homework" – не лист')
            send_error(error, bot)
            raise
        except my_ex.NotOKError as error:
            logger.exception('Код ответа не 200')
            send_error(error, bot)
            raise
        except my_ex.MessageSendError as error:
            logger.exception('Ошибка при отправке сообщения')
            send_error(error, bot)
            raise
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
