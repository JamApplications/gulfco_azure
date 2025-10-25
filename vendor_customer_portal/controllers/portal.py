# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo import conf, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.exceptions import AccessError, MissingError


class ContactPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(ContactPortal, self)._prepare_home_portal_values(counters)
        if 'customer_count' in counters:
            values['customer_count'] = 0
        if 'supplier_count' in counters:
            values['supplier_count'] = 0
        return values

    def _prepare_customer_sharing_session_info(self):
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        allowed_companies = {company.id: {'id': company.id, 'name': company.name}for company in request.env.user.company_ids}
        session_info.update(
            cache_hashes=cache_hashes,
            action_name='vendor_customer_portal.action_customer_portal',
            user_companies={
                'current_company': request.env.user.company_id.id,
                'allowed_companies': allowed_companies
            },
            currencies=request.env['ir.http'].get_currencies(),
        )
        return session_info
    #
    def action_customer_sharing(self):
        action = request.env['ir.actions.act_window']._for_xml_id(
            'vendor_customer_portal.action_customer_portal')
        return action

    @http.route("/my/customer_sharing", type="http", auth="user", methods=['GET'])
    def render_backend_view_customer(self):
        return request.render(
            'vendor_customer_portal.customer_sharing_embed',
            {'session_info': self._prepare_customer_sharing_session_info()},
        )

    @http.route(['/my/customer'], type='http',
                auth="user", website=True)
    def portal_my_customer(self):
        return request.render("vendor_customer_portal.customer_sharing_view")

    @http.route(['/my/supplier'], type='http',
                auth="user", website=True)
    def portal_my_supplier(self):
        return request.render("vendor_customer_portal.supplier_sharing_view")

    @http.route("/my/supplier_sharing", type="http", auth="user", methods=['GET'])
    def render_backend_view_supplier(self):
        return request.render(
            'vendor_customer_portal.supplier_sharing_embed',
            {'session_info': self._prepare_supplier_sharing_session_info()},
        )

    def _prepare_supplier_sharing_session_info(self):
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        allowed_companies = {company.id: {'id': company.id, 'name': company.name}for company in request.env.user.company_ids}
        session_info.update(
            cache_hashes=cache_hashes,
            action_name='vendor_customer_portal.action_vendor_portal',
            user_companies={
                'current_company': request.env.user.company_id.id,
                'allowed_companies': allowed_companies
            },
            currencies=request.env['ir.http'].get_currencies(),
        )
        return session_info