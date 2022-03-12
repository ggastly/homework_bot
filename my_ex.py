class NotOKError(Exception):
    def __init__(self, code_status):
        self.code_status = code_status
        super().__init__(
            f'API вернул код: {code_status}'
        )


class MissingRequiredTokens(Exception):
    def __init__(self, tokens):
        self.token = tokens
        super().__init__(
            f'Отсутствуют обязательные токены: {tokens}'
        )


class MessageSendError(Exception):
    def __init__(self):
        super().__init__(
            'Ошибка при отправке сообщения'
        )


class MissingRequiredKeys(Exception):
    def __init__(self):
        super().__init__(
            'Отсутствуют ожидаемые ключи в ответе API'
        )


class NoNewStatuses(Exception):
    def __init__(self):
        super().__init__(
            'Нет новых статусов'
        )


class UndocumentedStatus(Exception):
    def __init__(self):
        super().__init__(
            'API вернул недокументированный статус'
        )


class ErrorWithEndpoint(Exception):
    def __init__(self):
        super().__init__(
            'Проблема с доступом к эндпоинту'
        )


class HomeworkNotList(Exception):
    def __init__(self):
        super().__init__(
            'Под ключом "homeworks" не список'
        )


class HomeworksNotInResponse(Exception):
    def __init__(self):
        super().__init__(
            '"Homeworks" отсутствует в словаре'
        )
