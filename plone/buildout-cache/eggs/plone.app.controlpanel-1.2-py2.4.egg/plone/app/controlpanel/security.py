from zope.interface import Interface
from zope.component import adapts
from zope.formlib.form import FormFields
from zope.interface import implements
from zope.schema import Bool

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.ActionInformation import Action
from Products.CMFDefault.formlib.schema import SchemaAdapterBase
from Products.CMFPlone.utils import safe_hasattr
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.interfaces import IPloneSiteRoot

from form import ControlPanelForm

class ISecuritySchema(Interface):

    enable_self_reg = Bool(title=_(u'Enable self-registration'),
                        description=_(u"Allows users to register themselves "
                                      "on the site. If not selected, only site "
                                      "managers can add new users."),
                        default=False,
                        required=False)

    enable_user_pwd_choice = Bool(title=_(u'Let users select their \
own passwords'),
                        description=_(u"If not selected, passwords will be "
                                       "autogenerated and mailed to users, "
                                       "which verifies that they have entered "
                                       "a valid email address."),
                        default=False,
                        required=False)

    enable_user_folders = Bool(title=_(u'Enable User Folders'),
                        description=_(u"If selected, home folders "
                                       "where users can create content will "
                                       "be created when they log in."),
                        default=False,
                        required=False)

    allow_anon_views_about = Bool(title=_(u"Allow anyone to view 'about' "
                                           "information"),
                        description=_(u"If not selected only logged-in users "
                                       "will be able to view information about "
                                       "who created an item and when it was "
                                       "modified."),
                        default=False,
                        required=False)


class SecurityControlPanelAdapter(SchemaAdapterBase):

    adapts(IPloneSiteRoot)
    implements(ISecuritySchema)

    def __init__(self, context):
        super(SecurityControlPanelAdapter, self).__init__(context)
        pprop = getToolByName(context, 'portal_properties')
        self.pmembership = getToolByName(context, 'portal_membership')
        portal_url = getToolByName(context, 'portal_url')
        self.portal = portal_url.getPortalObject()
        self.context = pprop.site_properties

    def get_enable_self_reg(self):
        app_perms = self.portal.rolesOfPermission(permission='Add portal member')
        for appperm in app_perms:
            if appperm['name'] == 'Anonymous' and \
               appperm['selected'] == 'SELECTED':
                return True
        return False

    def set_enable_self_reg(self, value):
        app_perms = self.portal.rolesOfPermission(permission='Add portal member')
        reg_roles = []
        for appperm in app_perms:
            if appperm['selected'] == 'SELECTED':
                reg_roles.append(appperm['name'])
        if value == True and 'Anonymous' not in reg_roles:
            reg_roles.append('Anonymous')
        if value == False and 'Anonymous' in reg_roles:
            reg_roles.remove('Anonymous')

        self.portal.manage_permission('Add portal member', roles=reg_roles,
                                      acquire=0)

    enable_self_reg = property(get_enable_self_reg, set_enable_self_reg)


    def get_enable_user_pwd_choice(self):
        if self.portal.validate_email:
            return False
        else:
            return True

    def set_enable_user_pwd_choice(self, value):
        if value == True:
            self.portal.validate_email = False
        else:
            self.portal.validate_email = True

    enable_user_pwd_choice = property(get_enable_user_pwd_choice,
                                      set_enable_user_pwd_choice)


    def get_enable_user_folders(self):
        return self.pmembership.getMemberareaCreationFlag()

    def set_enable_user_folders(self, value):
        self.pmembership.memberareaCreationFlag = value
        # support the 'my folder' user action #8417
        portal_actions = getToolByName(self.portal, 'portal_actions', None)
        if portal_actions is not None:
            object_category = getattr(portal_actions, 'user', None)
            if value and not safe_hasattr(object_category, 'mystuff'):
                # add action
                self.add_mystuff_action(object_category)
            elif safe_hasattr(object_category, 'mystuff'):
                a = getattr(object_category, 'mystuff')
                a.visible = bool(value)    # show/hide action

    enable_user_folders = property(get_enable_user_folders,
                                   set_enable_user_folders)


    def add_mystuff_action(self, object_category):
        new_action = Action('mystuff',
                            title=_(u'My Folder'),
                            description='',
                            url_expr='string:${portal/portal_membership/getHomeUrl}',
                            available_expr='python:(member is not None) and \
                            (portal.portal_membership.getHomeFolder() is not None) ',
                            permissions=('View',),
                            visible=True,
                            i18n_domain='plone')
        object_category._setObject('mystuff', new_action)
        # move action to top, at least before the logout action
        object_category.moveObjectsToTop(('mystuff'))


    def get_allow_anon_views_about(self):
        return self.context.site_properties.allowAnonymousViewAbout

    def set_allow_anon_views_about(self, value):
        self.context.site_properties.allowAnonymousViewAbout = value

    allow_anon_views_about = property(get_allow_anon_views_about,
                                      set_allow_anon_views_about)


class SecurityControlPanel(ControlPanelForm):

    form_fields = FormFields(ISecuritySchema)

    label = _("Security settings")
    description = _("Security settings for this site.")
    form_name = _("Security settings")
