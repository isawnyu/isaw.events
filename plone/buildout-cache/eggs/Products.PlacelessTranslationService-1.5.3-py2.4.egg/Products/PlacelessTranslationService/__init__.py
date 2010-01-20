"""
$Id: __init__.py 83826 2009-04-04 15:54:31Z hannosch $
"""

import os
from zope.deprecation import deprecate

from Products.PageTemplates.GlobalTranslationService import \
    setGlobalTranslationService
from Globals import package_home
import Globals
pts_globals = globals()

from AccessControl import ModuleSecurityInfo, allow_module
from AccessControl.Permissions import view

from PlacelessTranslationService import PlacelessTranslationService
from PlacelessTranslationService import PTSWrapper
from PlacelessTranslationService import PTS_IS_RTL

import logging
from utils import log

from GettextMessageCatalog import purgeMoFileCache

# Apply import time patches
if not bool(os.getenv('DISABLE_PTS')):
    import patches

# id to use in the Control Panel
cp_id = 'TranslationService'

# module level translation service
translation_service = None

# icon
misc_ = {
    'PlacelessTranslationService.png':
    Globals.ImageFile('www/PlacelessTranslationService.png', globals()),
    'GettextMessageCatalog.png':
    Globals.ImageFile('www/GettextMessageCatalog.png', globals()),
    }

# set product-wide attrs for importing
security = ModuleSecurityInfo('Products.PlacelessTranslationService')
allow_module('Products.PlacelessTranslationService')

security.declareProtected(view, 'getTranslationService')
def getTranslationService():
    """returns the PTS instance
    """
    return translation_service

security.declareProtected(view, 'translate')
@deprecate("The translate method of the PTS package is deprecated and will be "
           "removed in the next PTS release. Use the translate method of the "
           "global translation service instead.")
def translate(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().translate(*args, **kwargs)

security.declareProtected(view, 'utranslate')
@deprecate("The utranslate method of the PTS package is deprecated and will be "
           "removed in the next PTS release. Use the translate method of the "
           "global translation service instead.")
def utranslate(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().translate(*args, **kwargs)

security.declareProtected(view, 'getLanguages')
@deprecate("The getLanguages method of the PTS package is deprecated and will "
           "be removed in the next PTS release. Use the getLanguages method on "
           "the translation service instead.")
def getLanguages(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().getLanguages(*args, **kwargs)

security.declareProtected(view, 'getLanguageName')
@deprecate("The getLanguageName method of the PTS package is deprecated and "
           "will be removed in the next PTS release. Use the getLanguageName "
           "method on the translation service instead.")
def getLanguageName(*args, **kwargs):
    """see PlaceslessTranslationService.PTSWrapper
    """
    return getTranslationService().getLanguageName(*args, **kwargs)

security.declareProtected(view, 'isRTL')
@deprecate("The isRTL method of the PTS package is deprecated and will be "
           "removed in the next PTS release. Use the information found in the "
           "Zope3 locale instead.")
def isRTL(context, domain):
    """Returns true for a rtl language and false for a ltr language
    """
    return getTranslationService().isRTL(context, domain)

def make_translation_service(cp):
    """Control_Panel translation service
    """
    global translation_service
    translation_service = PlacelessTranslationService('default')
    translation_service.id = cp_id
    cp._setObject(cp_id, translation_service)
    # We need to get the service in the context of the control panel so its
    # physical path is correct.
    cp_ts = getattr(cp, cp_id)
    translation_service = PTSWrapper(cp_ts)
    return cp_ts

def initialize2(context):
    # hook into the Control Panel
    global translation_service

    # allow for disabling PTS entirely by setting an environment variable.
    if bool(os.getenv('DISABLE_PTS')):
        log('Disabled by environment variable "DISABLE_PTS".', logging.WARNING)
        return

    cp = context._ProductContext__app.Control_Panel # argh
    if cp_id in cp.objectIds():
        cp_ts = getattr(cp, cp_id)
        # use the ts in the acquisition context of the control panel
        # translation_service = translation_service.__of__(cp)
        translation_service = PTSWrapper(cp_ts)
    else:
        cp_ts = make_translation_service(cp)

    # don't touch - this is the last version that didn't have the
    # attribute (0.4)
    instance_version = getattr(cp_ts, '_instance_version', (0, 4, 0, 0))
    if instance_version[3] > 99:
        log('development mode: translation service recreated',
            detail = '(found %s.%s.%s.%s)\n' % instance_version)
        cp._delObject(cp_id)
        cp_ts = make_translation_service(cp)

    if instance_version < PlacelessTranslationService._class_version:
        log('outdated translation service found, recreating',
            detail = '(found %s.%s.%s.%s)\n' % instance_version)
        cp._delObject(cp_id)
        purgeMoFileCache()
        cp_ts = make_translation_service(cp)

    # sweep products
    products = [getattr(p, 'package_name', 'Products.' + p.id) for
                p in cp.Products.objectValues() if
                getattr(p, 'thisIsAnInstalledProduct', False)]
    # Sort the products by lower-cased package name to gurantee a stable
    # load order
    products.sort(key=lambda p: p.lower())
    log('products: %r' % products, logging.DEBUG)
    for prod in products:
        # prod is a package name, we fake a globals dict with it
        try:
            prod_path = package_home({'__name__' : prod})
            cp_ts._load_i18n_dir(os.path.join(prod_path, 'i18n'))
        except KeyError:
            log("You have a stale entry for '%s' in your ZMI Products section."
                "You should consider removing it." % prod, logging.INFO)
            continue

    # sweep the i18n directory for local catalogs
    instance_i18n = os.path.join(Globals.INSTANCE_HOME, 'i18n')
    if os.path.isdir(instance_i18n):
        cp_ts._load_i18n_dir(instance_i18n)

    instance_locales = os.path.join(Globals.INSTANCE_HOME, 'locales')
    if os.path.isdir(instance_locales):
        cp_ts._load_locales_dir(instance_locales)

    # didn't found any catalogs
    if not cp_ts.objectIds():
        log('no translations found!', logging.DEBUG)

    # set ZPT's translation service
    # NOTE: since this registry is a global var we can't register the
    #       persistent service itself (zodb connection) therefore a
    #       wrapper is created around it
    setGlobalTranslationService(PTSWrapper(cp_ts))
