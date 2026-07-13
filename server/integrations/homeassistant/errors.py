class HomeAssistantError(RuntimeError):
    user_message = "Le service domotique est actuellement indisponible."


class HomeAssistantUnavailable(HomeAssistantError):
    pass


class HomeAssistantApiError(HomeAssistantError):
    pass


class HomeAssistantAuthError(HomeAssistantError):
    pass


class HomeAssistantEntityNotFound(HomeAssistantError):
    user_message = "Je n'ai trouvé aucun équipement correspondant."
