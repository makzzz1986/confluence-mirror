import os
import sys
from conf_page import *
from loguru import logger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_JSON = os.environ.get("LOG_JSON", "false")
LOG_JSON_BOOL = True if LOG_JSON.lower() == "true" else False
logger.remove()  # remove default logger
logger.add(
    sys.stdout,
    format="{time} {level} {message}",
    serialize=LOG_JSON_BOOL,
    level=LOG_LEVEL,
)


CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL")
USER_EMAIL = os.environ.get("USER_EMAIL")
USER_TOKEN = os.environ.get("USER_TOKEN")
SPACE_KEY = os.environ.get("SPACE_KEY")
DEPTH = os.environ.get("DEPTH", "2")
BACKUP_PATH = os.environ.get("BACKUP_PATH", "/tmp/conf_backup")
EXCLUSIONS_LIST = os.environ.get("EXCLUSIONS_LIST", "notes,draft,handover")
FAVICON_URL = os.environ.get("FAVICON_URL", None)


if USER_TOKEN and USER_EMAIL and CONFLUENCE_URL and SPACE_KEY:
    conf = Conf_API(
        confluence_url=CONFLUENCE_URL,
        username=USER_EMAIL,
        api_token=USER_TOKEN,
        logger=logger,
    )

    conf.download_space(
        space=SPACE_KEY, path=BACKUP_PATH, max_depth=int(DEPTH), limit=50, exclusions_list=EXCLUSIONS_LIST.split(","), favicon_url=FAVICON_URL
    )
else:
    print(
        f"Some of the required environment variables are missing, please set CONFLUENCE_URL [{'V' if CONFLUENCE_URL else 'X'}], USER_EMAIL [{'V' if USER_EMAIL else 'X'}], USER_TOKEN [{'V' if USER_TOKEN else 'X'}], and SPACE_KEY [{'V' if SPACE_KEY else 'X'}]."
    )
