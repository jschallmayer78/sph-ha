DOMAIN = "sph"
CONF_SCHOOL_ID = "school_id"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CHILD_NAME = "child_name"
CONF_CHILD_SHORTCUT = "child_shortcut"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_FIRST_LESSON = "first_lesson"
DEFAULT_UPDATE_INTERVAL = 60
# School lesson that the "first lesson cancelled" binary sensors look at.
DEFAULT_FIRST_LESSON = 1

PLATFORMS = ["binary_sensor", "calendar", "sensor"]

# Authentication is hosted separately from the legacy school portal.
SPH_BASE = "https://start.schulportal.hessen.de"
SPH_LOGIN = "https://login.schulportal.hessen.de/"
SPH_CONNECT = "https://connect.schulportal.hessen.de/"
