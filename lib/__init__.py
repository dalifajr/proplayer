"""lib — internal modules for GitHub Edu Pro.

core.py re-exports everything from these modules for backward compatibility.
Direct usage:  ``from lib.auth import login_with_cookie_str``
Via facade:    ``from core import login_with_cookie_str``   (same result)
"""

from lib.config import *      # noqa: F401,F403
from lib.htmlparse import *   # noqa: F401,F403
from lib.auth import *        # noqa: F401,F403
from lib.totp import *        # noqa: F401,F403
from lib.school import *      # noqa: F401,F403
from lib.idcard import *      # noqa: F401,F403
from lib.github import *      # noqa: F401,F403
from lib.pipeline import *    # noqa: F401,F403
