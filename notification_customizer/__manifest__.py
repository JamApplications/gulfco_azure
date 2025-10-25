{
    'name': 'Notification Customizer',
    'version': '1.0',
    'summary': 'Send model-based notifications based on state, groups, and users',
    'category': 'Tools',
    'depends': ['base', 'mail'],
    'data': [
        'views/notification_config_views.xml',
        # 'data/data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
