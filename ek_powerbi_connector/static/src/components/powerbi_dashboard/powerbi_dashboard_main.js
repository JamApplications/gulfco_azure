/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onWillStart, onMounted, useState } from "@odoo/owl";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";


export class PowerBIDashboardMain extends Component {
    setup(){
        this.state = useState({
          powerBIReports: {},
          sideBarActiveIndex: null,
          isLoadingDashboard: true,
          powerBIUserInfo: session.powerbi_user_info,
          powerBIReportName: null
        })
        this.baseUrl = session.base_url;
        this.powerbi_access_token = session.powerbi_access_token;
        this.powerbi_refresh_token = session.powerbi_refresh_token;
        this.powerbi_access_token_info = session.powerbi_access_token_info
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.signinButtonRef = useRef("powerbi-signin")
        this.powerBIReportContainer = useRef('powerbi-report-container')
        this.powerBIGroupId = null
        this.powerBIReportId = null

        onWillStart(async () => {
          this.state.powerBIReports = await this.getPowerBIReports()
          this.addPowerBIReportInfo()
          this.is_powerbi_logged_in = await this.isPowerBILoggedIn()
        })

        onMounted(async () => {
          this.viewPowerBIReport()
        });

    }

    addPowerBIReportInfo() {
      const powerBIReportKeys = Object.keys(this.state.powerBIReports)
      if (powerBIReportKeys.length > 0) {
        this.state.sideBarActiveIndex = powerBIReportKeys[0]
        this.powerBIGroupId = this.state.powerBIReports[powerBIReportKeys[0]].group_id
        this.powerBIReportId = this.state.powerBIReports[powerBIReportKeys[0]].report_id
        this.state.powerBIReportName = this.state.powerBIReports[powerBIReportKeys[0]].name
      }
    }

    async getPowerBIReports() {
      const result = await this.orm.searchRead("pb.dashboard.configuration", [],
                      ["name", "description", "report_tag_id", "group_id", "report_id"])
      const finalValue = this.convertListToDict(result)
      return finalValue
    }

    async onClickReportItem(reportId) {
      this.hidePowerBIContainer()
      this.state.sideBarActiveIndex = reportId
      this.state.powerBIReportName = this.state.powerBIReports[reportId].name
      this.powerBIGroupId = this.state.powerBIReports[reportId].group_id
      this.powerBIReportId = this.state.powerBIReports[reportId].report_id
      this.viewPowerBIReport()
    }

    async isPowerBILoggedIn(){
      if (this.powerbi_refresh_token) {
        if (this.isAccessTokenExpired()) {
          await this.refreshPowerBIToken()
        }
        return true
      }
      else {
        return false
      }
    }

    isAccessTokenExpired() {
      const currentEpochTimeInSeconds = (Math.floor(Date.now() / 1000) + 5);
      if (currentEpochTimeInSeconds > this.powerbi_access_token_info.exp) {
        return true
      }
      return false
    }

    async refreshPowerBIToken() {
      try {
        const result = await rpc("/powerbi/embed/oauth/refresh/token");
        if (result.success) {
          this.updateTokenInformations(result)
        }
        else {
          await this.signoutPowerBI()
        }
      } catch (err) {
        await this.signoutPowerBI()
      }
    }

    updateTokenInformations(result){
      this.powerbi_access_token = result.success.response.access_token
      this.powerbi_refresh_token = result.success.response.refresh_token
      this.powerbi_access_token_info = this.getAccessTokenInfo()
      this.state.powerBIUserInfo = this.getPowerBIUserInfo(result.success.response.id_token)
    }

    async powerBISignin() {
      try {
        const result = await rpc("/powerbi/embed/oauth/login");
        if (result.authUrl) {
          window.location.replace(result.authUrl);
        }
      } catch (err) {
        console.error("Authentication failed:", err);
      }
    }

    async signoutPowerBI() {
      await rpc("/powerbi/embed/signout");
      this.actionService.doAction({
        type: 'ir.actions.client',
        tag: 'reload'
      })
    }

    async viewPowerBIReport() {
      if (!this.is_powerbi_logged_in) {
        return
      }
      if (this.isAccessTokenExpired()) {
        await this.refreshPowerBIToken()
      }
      await this.embedPowerBIReport()
      this.showPowerBIContainer()
    }

    async embedPowerBIReport() {
      const headers = new Headers({
        'Authorization': `Bearer ${this.powerbi_access_token}`
      });

      const res = await fetch(`https://api.powerbi.com/v1.0/myorg/groups/${this.powerBIGroupId}/reports/${this.powerBIReportId}`, {
        method: 'GET',
        headers: headers
      });

      const report = await res.json();

      const embedConfig = {
        type: 'report',
        id: report.id,
        embedUrl: report.embedUrl,
        accessToken: this.powerbi_access_token,
        tokenType: window['powerbi-client'].models.TokenType.Aad,
        settings: {
          panes: {
            filters: { visible: false },
            pageNavigation: { visible: true }
          }
        }
      };
      powerbi.embed(this.powerBIReportContainer.el, embedConfig);
    }

    showPowerBIContainer() {
      if (!this.is_powerbi_logged_in) {
        return
      }
      this.state.isLoadingDashboard = false
      this.powerBIReportContainer.el.classList.remove('d-none')
    }

    hidePowerBIContainer() {
      if (!this.is_powerbi_logged_in) {
        return
      }
      this.state.isLoadingDashboard = true
      powerbi.reset(this.powerBIReportContainer.el);
      this.powerBIReportContainer.el.classList.add('d-none')
    }

    convertListToDict(list) {
      return list.reduce((acc, item) => {
          acc[item.id] = item;
          return acc;
      }, {});
    }

    getAccessTokenInfo() {
      const payload = this.decodeJwtPayload(this.powerbi_access_token);
      return {
         'exp': payload['exp']
      }
    }

    getPowerBIUserInfo(idToken) {
      const payload = this.decodeJwtPayload(idToken);
      return {
        'name': payload['name'],
        'email': payload['email'],
      }
    }

    onSearchSiderBarInput(ev) {
      const clearHighlight = this.clearHighlight
      const highlightText = this.highlightText

      const filter = ev.target.value.trim().toLowerCase();
      const items = document.getElementsByClassName('search-pb-report-item');
      Array.from(items).forEach(function (item) {
          const titleElem = item.querySelector('strong');
          const descElem = item.querySelector('.small');
          const badgeElem = item.querySelector('.badge');

          // Clear previous highlights
          clearHighlight(titleElem);
          clearHighlight(descElem);
          if (badgeElem) clearHighlight(badgeElem);

          const titleText = titleElem?.textContent.toLowerCase() || '';
          const descText = descElem?.textContent.toLowerCase() || '';
          const badgeText = badgeElem?.textContent.toLowerCase() || '';

          if (titleText.includes(filter) || descText.includes(filter) || badgeText.includes(filter)) {
              item.style.display = '';

              // Apply highlight only if filter is not empty
              if (filter) {
                  titleElem.innerHTML = highlightText(titleElem, filter);
                  descElem.innerHTML = highlightText(descElem, filter);
                  if (badgeElem) badgeElem.innerHTML = highlightText(badgeElem, filter);
              }

          } else {
              item.style.display = 'none';
          }
      });
    }

    highlightText(element, text) {
      if (!text) {
          return element.textContent;
      }
      const regex = new RegExp(`(${text})`, 'gi');
      return element.textContent.replace(regex, '<span class="highlight-search-text">$1</span>');
    }

    clearHighlight(element) {
      element.innerHTML = element.textContent;
    }

    decodeJwtPayload(token) {
      const parts = token.split('.');
      if (parts.length !== 3) {
          throw new Error('Invalid JWT token');
      }

      let payload = parts[1];

      // Add padding if missing (Base64url might skip '=' padding)
      payload = payload.replace(/-/g, '+').replace(/_/g, '/');
      while (payload.length % 4 !== 0) {
          payload += '=';
      }

      // Decode Base64 to JSON string
      const jsonPayload = atob(payload);
      // Parse JSON string
      return JSON.parse(jsonPayload);
    }

}

PowerBIDashboardMain.template = "ek_powerbi_connector.PowerBIDashboardMain"
PowerBIDashboardMain.components = { }

registry.category("actions").add("ek_powerbi_connector_dashboard_main", PowerBIDashboardMain)
