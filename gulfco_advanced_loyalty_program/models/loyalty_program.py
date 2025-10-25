from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    program_type = fields.Selection(
        selection_add=[('ladder_promotion', 'Ladder Promotion'),('slab_promotion', 'Slab Promotion'),('flat_discount', 'Flat Discount')],
        ondelete={'ladder_promotion': 'set default','slab_promotion': 'set default','flat_discount': 'set default'},  # this must be a dict
    )

    promo_product_group_id = fields.Many2one('promo.product.group', string="Product Group")
    promo_customer_group_id = fields.Many2one('promo.customer.group', string="Customer Group")
    ladder_rule_ids = fields.One2many('promo.ladder.rule', 'promo_program_id', string="Ladder Rules")
    discount_line_product_id = fields.Many2one('product.product',domain=[('type','=','service'),('sale_ok','=',False),
                                                                         ('purchase_ok','=',False),('available_in_pos','=',False),
                                                                         ('can_be_expensed','=', False)], string="Discount Line Product")


    # 2) One2many to your slab rules
    slab_rule_ids = fields.One2many(
        'promo.slab.rule',
        'promo_program_id',
        string="Slab Rules",
        help="Define invoice‑value ranges and discounts"
    )

    # 2) Reuse Customer Group, add Flat‑specific targets:
    flat_division       = fields.Selection([
        ('non_food', 'Non‑Food'),
        ('mars',      'Mars'),
        ('food',      'Food'),
    ], string="Division")

    flat_product_ids = fields.Many2many(
            'product.product',
            string = "Products",
        help = "Select one or more products for flat discount")
    flat_discount_percentage = fields.Float(string="Discount %", digits=(5, 2))


    flat_discount_apply_options = fields.Selection([('division',"Division"),('product_group','Products Group'),('products','Products')],
                                                   default='division')

    flat_apply_customers_options = fields.Selection([('customer_group',"Customers Group"),('customer','Customers')],
                                                   default='customer_group')

    flat_customer_ids = fields.Many2many('res.partner', string="Customers", domain=[('contact_type','in', ['customer','both']), ('active','=',True)])


    def _is_customer_allowed(self, order):
        """Helper: if a customer‐group filter is set, reject others."""
        if self.promo_customer_group_id:
            return order.partner_id in self.promo_customer_group_id.partner_ids
        return True


    def is_ladder_applicable(self, order):
        self.ensure_one()
        # 0) customer check
        if not self._is_customer_allowed(order):
            return False
        # count distinct eligible products on the order
        if order.partner_id not in self.promo_customer_group_id.partner_ids:
            return False
        prods = self.promo_product_group_id.product_ids.ids
        bought = set(order.order_line
                          .filtered(lambda l: l.product_id.id in prods)
                          .mapped('product_id'))
        return bool(self.ladder_rule_ids.filtered(lambda r: r.distinct_item_count <= len(bought)))

    def is_slab_applicable(self, order):
        self.ensure_one()
        # 0) customer check
        if not self._is_customer_allowed(order):
            return False
        prods = self.promo_product_group_id.product_ids.ids
        applicable_lines = order.order_line.filtered(lambda l: l.product_id.id in prods)
        if not applicable_lines:
            return False
        exercise_price = [(i.exercise_price * i.product_uom_qty) for i in order.order_line.filtered(
            lambda l: l.product_id.id in prods)]
        total = sum(applicable_lines.mapped('price_subtotal')) - sum(exercise_price)
        return bool(self.slab_rule_ids.filtered(lambda r: total >= r.min_amount and total <= r.max_amount))

    def is_flat_applicable(self, order):
        self.ensure_one()
        # 0) customer
        if self.flat_apply_customers_options == 'customer_group' and self.promo_customer_group_id:
            if order.partner_id not in self.promo_customer_group_id.partner_ids:
                return False
        elif self.flat_apply_customers_options == 'customer':
            if order.partner_id not in self.flat_customer_ids:
                return False
        # 1) line filter
        lines = order.order_line
        opt = self.flat_discount_apply_options
        if opt == 'division' and self.flat_division:
            lines = lines.filtered(lambda l: l.product_id.division == self.flat_division)
        elif opt == 'product_group' and self.promo_product_group_id:
            gids = self.promo_product_group_id.product_ids.ids
            lines = lines.filtered(lambda l: l.product_id.id in gids)
        elif opt == 'products' and self.flat_product_ids:
            pids = self.flat_product_ids.ids
            lines = lines.filtered(lambda l: l.product_id.id in pids)
        else:
            return False
        return bool(lines)


    # 3) Exactly one target must be set
    @api.constrains('flat_division', 'promo_product_group_id', 'flat_product_ids')
    def _check_flat_target_xor(self):
        for prog in self.filtered(lambda p: p.program_type == 'flat_discount'):
            vals = bool(prog.flat_division) + bool(prog.promo_product_group_id) + bool(prog.flat_product_ids)
            if vals != 1:
                raise ValidationError(_("For a Flat Discount you must select exactly one of Division, Product Group, or Single Product. %s" %(vals)))


    @api.onchange('slab_rule_ids', 'program_type')
    def _onchange_slab_rules_generate_rewards(self):
        """Whenever slab rules change on a slab_promotion, rebuild reward_ids."""
        for program in self:
            if program.program_type != 'slab_promotion':
                continue
            # 1) clear out any old rewards
            program.reward_ids = [(5, 0, 0)]
            # 2) build a new reward for *each* slab rule
            new_rewards = []
            for rule in program.slab_rule_ids:
                new_rewards.append((0, 0, {
                    'reward_type':             'discount',
                    'discount_mode':           'percent',
                    'discount':                rule.discount_percentage,
                    'discount_applicability':  'order',
                    'required_points':         1,
                    'description':             _(
                       'Invoice %s - %s → %s%% off',
                        rule.min_amount, rule.max_amount, rule.discount_percentage
                    ),
                    'discount_line_product_id': program.discount_line_product_id.id,
                }))
            program.reward_ids = new_rewards

    @api.constrains('slab_rule_ids', 'program_type')
    def _constrains_slab_rules_generate_rewards(self):
        for program in self:
            if program.program_type != 'slab_promotion':
                continue
            program._onchange_slab_rules_generate_rewards()


    def _get_or_create_flat_reward(self):
        self.ensure_one()
        reward = self.reward_ids[:1]
        if not reward:
            reward = self.env['loyalty.reward'].create({
                'program_id': self.id,
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': _('Flat discount'),
                'discount_line_product_id': self.discount_line_product_id.id,
            })
            self.reward_ids = [(4, reward.id)]
        return reward


    def _write_reward_safely(self, reward, vals):
        # Drop keys that wouldn't change (prevents useless jsonb UPDATEs)
        clean = {}
        for k, v in vals.items():
            try:
                if reward[k] != v:
                    clean[k] = v
            except Exception:
                clean[k] = v
        if clean:
            # Row-level lock via ORM (Odoo standard): prevents cross-updates deadlocking
            reward.sudo().write(clean)
        return reward

    def update_flat_reward(self):
        self.ensure_one()
        reward = self._get_or_create_flat_reward()
        pct = self.flat_discount_percentage or 0.0
        return self._write_reward_safely(reward, {
            'discount': pct,
            'description': _('Flat %s%% off') % pct,
        })

    def update_slab_reward_from_rule(self, rule):
        reward = self._get_or_create_slab_reward()
        return self._write_reward_safely(reward, {
            'discount': rule.discount_percentage,
            'description': _(
                'Invoice value %s - %s → %s%% off',
                rule.min_amount, rule.max_amount, rule.discount_percentage
            ),
        })

    def update_ladder_reward_from_rule(self, rule):
        reward = self._get_or_create_ladder_reward()
        return self._write_reward_safely(reward, {
            'discount': rule.discount_percentage,
            'description': _('Buy %s items → %s%% off') % (
                rule.distinct_item_count, rule.discount_percentage),
        })



    # 3) Ensure exactly one loyalty.reward for slabs
    @api.onchange('program_type', 'discount_line_product_id')
    def _ensure_single_slab_reward(self):
        for program in self:
            if program.program_type != 'slab_promotion':
                continue
            # If none, create a blank one
            if not program.reward_ids:
                program.reward_ids = [(0, 0, {
                    'program_id': program.id,
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 1,
                    'discount_applicability': 'order',
                    'required_points': 1,
                    'description': _('Slab discount'),
                    'discount_line_product_id': program.discount_line_product_id.id,
                })]
            # If multiple by mistake, keep only the first
            elif len(program.reward_ids) > 1:
                keep = program.reward_ids[:1]
                program.reward_ids = [(6, 0, keep.ids)]

    def _get_or_create_slab_reward(self):
        """Returns the single reward record for this slab program."""
        self.ensure_one()
        reward = self.reward_ids[:1]
        if not reward:
            reward = self.env['loyalty.reward'].create({
                'program_id': self.id,
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': _('Slab discount'),
                'discount_line_product_id': self.discount_line_product_id.id,
            })
            self.reward_ids = [(4, reward.id)]
        return reward


    @api.onchange('program_type', 'discount_line_product_id')
    def _ensure_single_ladder_reward(self):
        """Create a single placeholder reward when the type is ladder_promotion."""
        for program in self:
            if program.program_type != 'ladder_promotion':
                continue
            # If no reward exists yet, create one blank
            if not program.reward_ids:
                program.reward_ids = [(0, 0, {
                    'program_id': program.id,
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 1,
                    'discount_applicability': 'order',
                    'required_points': 1,
                    'description': _('Ladder discount'),
                    'discount_line_product_id': program.discount_line_product_id.id,
                })]
            # If more than one somehow, keep only the first
            elif len(program.reward_ids) > 1:
                keep = program.reward_ids[:1]
                program.reward_ids = [(6, 0, keep.ids)]

    # models/loyalty_program.py (same file, under the above)
    def _get_or_create_ladder_reward(self):
        self.ensure_one()
        reward = self.reward_ids[:1]
        if not reward:
            # fallback in case someone deleted it
            reward = self.env['loyalty.reward'].create({
                'program_id': self.id,
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': _('Ladder discount'),
                'discount_line_product_id': self.discount_line_product_id.id,
            })
            self.reward_ids = [(4, reward.id)]
        return reward

    # ——————————————————————————————————————————————
    # 1) On‑change in the form, immediately update your loyalty.rule lines
    # ——————————————————————————————————————————————
    @api.onchange('promo_product_group_id')
    def _onchange_promo_product_group_id(self):
        if self.program_type == 'ladder_promotion':
            product_ids = self.promo_product_group_id.product_ids.ids if self.promo_product_group_id else []
            # overwrite *all* loyalty.rule.product_ids for this program
            for rule in self.rule_ids:
                rule.product_ids = [(6, 0, product_ids)]

    @api.onchange('promo_customer_group_id')
    def _onchange_promo_customer_group_id(self):
        if self.program_type == 'ladder_promotion':
            partner_ids = self.promo_customer_group_id.partner_ids.ids if self.promo_customer_group_id else []
            for rule in self.rule_ids:
                # assumes loyalty.rule has a partner_ids m2m field
                rule.customer_ids = [(6, 0, partner_ids)]

    # ——————————————————————————————————————————————
    # 1) On‑change in the form, immediately update your loyalty.rule lines
    # ——————————————————————————————————————————————
    @api.constrains('promo_product_group_id')
    def _constrains_promo_product_group_id(self):
        if self.program_type == 'ladder_promotion':
            product_ids = self.promo_product_group_id.product_ids.ids if self.promo_product_group_id else []
            # overwrite *all* loyalty.rule.product_ids for this program
            for rule in self.rule_ids:
                rule.product_ids = [(6, 0, product_ids)]

    @api.constrains('promo_customer_group_id')
    def _constrains_promo_customer_group_id(self):
        if self.program_type == 'ladder_promotion':
            partner_ids = self.promo_customer_group_id.partner_ids.ids if self.promo_customer_group_id else []
            for rule in self.rule_ids:
                # assumes loyalty.rule has a partner_ids m2m field
                rule.customer_ids = [(6, 0, partner_ids)]


    @api.onchange('ladder_rule_ids', 'program_type')
    def _onchange_ladder_rules_generate_rewards(self):
        """ Whenever you change ladder rules on a ladder‑promotion, rebuild reward_ids """
        for program in self:
            if program.program_type != 'ladder_promotion':
                continue
            # 1) Clear out old rewards
            program.reward_ids = [(5, 0, 0)]
            # 2) Build a new reward for each ladder rule
            new_rewards = []
            for rule in program.ladder_rule_ids:
                new_rewards.append((0, 0, {
                    'reward_type':        'discount',
                    'discount_mode':      'percent',
                    'discount':           rule.discount_percentage,
                    'discount_applicability': 'order',
                    # points not used in a pure-promo context:
                    'required_points':    1,
                    'description':        _('Buy %s items → %s%% off') % (
                                              rule.distinct_item_count,
                                              rule.discount_percentage),
                    'discount_line_product_id': program.discount_line_product_id.id,
                }))
            program.reward_ids = new_rewards

    @api.constrains('ladder_rule_ids', 'program_type')
    def _constrains_ladder_rules_generate_rewards(self):
        for program in self:
            if program.program_type != 'ladder_promotion':
                continue
            program._onchange_ladder_rules_generate_rewards()



    @api.onchange('program_type', 'discount_line_product_id')
    def _ensure_single_flat_reward(self):
        for prog in self:
            if prog.program_type != 'flat_discount':
                continue
            if not prog.reward_ids:
                prog.reward_ids = [(0, 0, {
                    'program_id': prog.id,
                    'reward_type': 'discount',
                    'discount_mode': 'percent',
                    'discount': 1,
                    'discount_applicability': 'order',
                    'required_points': 1,
                    'description': _('Flat discount'),
                    'discount_line_product_id': prog.discount_line_product_id.id,
                })]
            elif len(prog.reward_ids) > 1:
                keep = prog.reward_ids[:1]
                prog.reward_ids = [(6, 0, keep.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        programs = super().create(vals_list)
        # ensure one placeholder reward for each new program
        for prog in programs:
            categ_id = False
            if prog.program_type == 'flat_discount':
                prog._ensure_single_flat_reward()
                categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_flat_discount', False)
                categ_id = categ_id.id
            elif prog.program_type == 'slab_promotion':
                prog._ensure_single_slab_reward()
                categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_slab_discount', False)
                categ_id = categ_id.id
            elif prog.program_type == 'ladder_promotion':
                prog._ensure_single_ladder_reward()
                categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_ladder_discount', False)
                categ_id = categ_id.id
            else:
                categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_other_promotions', False)
                categ_id = categ_id.id

            if not prog.discount_line_product_id:
                # build a unique name: e.g. "Summer Sale (Slab Promotion)"
                ptype_label = dict(self._fields['program_type'].selection).get(prog.program_type)
                prod_name = _("%s (%s)") % (prog.name, ptype_label or 'Promo')

                service_product = self.env['product.product'].create({
                    'name': prod_name,
                    'type': 'service',
                    'sale_ok': False,
                    'purchase_ok': False,
                    'available_in_pos': False,
                    'can_be_expensed': False,
                    'invoice_policy': 'order',
                    'categ_id': categ_id,
                })
                prog.discount_line_product_id = service_product

        return programs

    def write(self, vals):
        self = self.with_context(loyalty_skip_reward_check=True)
        res = super().write(vals)
        # if program_type flipped, inject the placeholder reward
        if 'program_type' in vals or 'discount_line_product_id' in vals:
            for prog in self:
                categ_id = False
                if prog.program_type == 'flat_discount':
                    prog._ensure_single_flat_reward()
                    categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_flat_discount', False)
                    categ_id = categ_id.id

                elif prog.program_type == 'slab_promotion':
                    prog._ensure_single_slab_reward()
                    categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_slab_discount', False)
                    categ_id = categ_id.id

                elif prog.program_type == 'ladder_promotion':
                    prog._ensure_single_ladder_reward()
                    categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_ladder_discount', False)
                    categ_id = categ_id.id

                else:
                    categ_id = self.env.ref('gulfco_advanced_loyalty_program.category_other_promotions', False)
                    categ_id = categ_id.id

                if ('program_type' in vals or not prog.discount_line_product_id) and prog.program_type:
                    ptype_label = dict(self._fields['program_type'].selection).get(prog.program_type)
                    prod_name = _("%s (%s)") % (prog.name, ptype_label or 'Promo')


                    # reuse existing if it matches, otherwise create new
                    existing = prog.discount_line_product_id
                    if not existing or existing.name != prod_name:
                        service_product = self.env['product.product'].create({
                            'name': prod_name,
                            'type': 'service',
                            'sale_ok': False,
                            'purchase_ok': False,
                            'available_in_pos': False,
                            'can_be_expensed': False,
                            'invoice_policy': 'order',
                            'categ_id': categ_id,
                        })
                        prog.discount_line_product_id = service_product
        return res
    @api.model
    def _program_items_name(self):
        # Get existing items from parent
        items = super(LoyaltyProgram, self)._program_items_name()
        # Clearly add your custom key here
        items.update({
            'ladder_promotion': _('Ladder Promotion'),
            'slab_promotion': _('Slab Promotion'),
            'flat_discount': _('Flat Discount'),
        })
        return items

class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    def write(self, vals):
        # ensure any downstream writes (e.g. discount_line_product_id.write) carry the flag
        self = self.with_context(_skip_discount_product_rename=True)
        return super().write(vals)

    @api.depends('reward_type', 'discount_applicability', 'discount_mode')
    def _compute_is_global_discount(self):
        for reward in self:
            if reward.program_id.program_type in ['slab_promotion','ladder_promotion']:
                reward.is_global_discount = False
            else:
                reward.is_global_discount = (
                    reward.reward_type == 'discount'
                    and reward.discount_applicability == 'order'
                    and reward.discount_mode in ['per_order', 'percent']
                )
