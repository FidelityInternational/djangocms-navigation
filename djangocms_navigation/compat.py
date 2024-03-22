from packaging.version import Version
from treebeard import __version__ as treebeard_version


TREEBEARD_4_5 = Version(treebeard_version) < Version('4.6')
