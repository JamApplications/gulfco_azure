/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { browser } from "@web/core/browser/browser";
import { Component } from "@odoo/owl";





/* global html2canvas */


//import { html2canvas } from "./html2canvas.js"
//import { HtmlCanvas } from "@web_editor/static/lib/html2canvas"
import { loadJS } from "@web/core/assets";





publicWidget.registry.StateSelection = publicWidget.Widget.extend({
    selector: '.state_selection',
    events: { 'click': '_onCountryChange' },


    async _onCountryChange (event) {
            debugger;
        const countrySelect = document.getElementById('country_id');
        const stateSelect = document.getElementById('state_id');
        const countryId = countrySelect.value;

        if (countryId) {
            // Clear current state options
            stateSelect.innerHTML = '<option value="">Loading...</option>';

            try {
                const data = await rpc('/portal/get_states', {
                    country_id: countryId,
                });

                stateSelect.innerHTML = '<option value="">Select State</option>';
                data.forEach((state) => {
                    const option = document.createElement('option');
                    option.value = state.id;
                    option.textContent = state.name;
                    stateSelect.appendChild(option);
                });
            } catch (error) {
                console.error("Error fetching states:", error);
            }
        } else {
            // Reset state dropdown if no country selected
            stateSelect.innerHTML = '<option value="">Select State</option>';
        }
    }
})



publicWidget.registry.ChannelSelection = publicWidget.Widget.extend({
    selector: '.channel_selection',
    events: { 'click': '_onChannelChange' },

    async _onChannelChange (event) {
            debugger;
        const channelSelect = document.getElementById('channel');
        const SubChannel1 = document.getElementById('sub_channel1');
        const SubChannel2 = document.getElementById('sub_channel2');
        const ChannelID = channelSelect.value;

        if (ChannelID) {
            // Clear current state options
            SubChannel1.innerHTML = '<option value="">Loading...</option>';
            SubChannel2.innerHTML = '<option value="">Loading...</option>';

            try {
                const data = await rpc('/get/channel/1', {
                    channel_id: ChannelID,
                });

                SubChannel1.innerHTML = '<option value="">Select SubChannel 1</option>';
                data.forEach((state) => {
                    const option = document.createElement('option');
                    option.value = state.key;
                    option.textContent = state.value;
                    SubChannel1.appendChild(option);
                });
            } catch (error) {
                console.error("Error fetching states:", error);
            }
        } else {
            // Reset state dropdown if no country selected
            SubChannel1.innerHTML = '<option value="">Select SubChannel 1</option>';
            SubChannel2.innerHTML = '<option value="">Select SubChannel 1</option>';
        }
    }
})


publicWidget.registry.SubChannelSelection = publicWidget.Widget.extend({
    selector: '.sub_channel_selection',
    events: { 'click': '_onSubChannelChange' },

    async _onSubChannelChange (event) {
            debugger;
        const SubChannelSelect = document.getElementById('sub_channel1');
        const sub_channel2 = document.getElementById('sub_channel2');
        const SubChannelID = SubChannelSelect.value;

        if (SubChannelID) {
            // Clear current state options
            sub_channel2.innerHTML = '<option value="">Loading...</option>';

            try {
                const data = await rpc('/get/sub/channel/2', {
                    sub_channel_id: SubChannelID,
                });

                sub_channel2.innerHTML = '<option value="">Select SubChannel 2</option>';
                data.forEach((state) => {
                    const option = document.createElement('option');
                    option.value = state.key;
                    option.textContent = state.value;
                    sub_channel2.appendChild(option);
                });
            } catch (error) {
                console.error("Error fetching states:", error);
            }
        } else {
            // Reset state dropdown if no country selected
            sub_channel2.innerHTML = '<option value="">Select SubChannel 2</option>';
        }
    }
})



publicWidget.registry.VendorDateValidation = publicWidget.Widget.extend({
//    selector: 'form[action="/submit_vendor_registration"]',
//      events: {
//            'submit': '_onFormSubmit',
//        },
    selector: '.expiry_date_selection',
    events: {
        'input #expiry_date': '_onChangeExpiryDate',
        'input #issued_date': '_onChangeExpiryDate',
    },




//    _onFormSubmit: function (ev) {
    _onChangeExpiryDate: function (ev) {
        const issuedDateInput = document.querySelector('input[name="issued_date"]');
        const expiryDateInput = document.querySelector('input[name="expiry_date"]');

        if (!issuedDateInput || !expiryDateInput) return;

        const issuedDate = new Date(issuedDateInput.value);
        const expiryDate = new Date(expiryDateInput.value);
        const today = new Date();

        // Normalize today's time
        issuedDate.setHours(0, 0, 0, 0);
        expiryDate.setHours(0, 0, 0, 0);
        today.setHours(0, 0, 0, 0);

        // Validation 1: Expiry date should be greater than issue date
        if (expiryDate < issuedDate) {
            ev.preventDefault();
             expiryDateInput.value = '';
             this.call("dialog", "add", AlertDialog, {
                title: "Validation Error",
                body: "Expiry date must be greater than the issue date.",
                className: "custom-alert-dialog",
            });
            return false;
        }

        // Validation 2: Expiry date should not be same as issue date
        if (expiryDate.getTime() === issuedDate.getTime()) {
            ev.preventDefault();
            expiryDateInput.value = '';
            this.call("dialog", "add", AlertDialog, {
                title: "Validation Error",
                body: "Expiry date should not be the same as the issue date.",
                className: "custom-alert-dialog",
            });
            return false;
        }

        // Validation 3: Expiry date should not be a past date
        if (expiryDate <= today) {
            ev.preventDefault();
            expiryDateInput.value = '';
           this.call("dialog", "add", AlertDialog, {
                title: "Validation Error",
                body: "Expiry date must be a future date.",
                className: "custom-alert-dialog",
            });
            return false;
        }

        // Validation 4: Issue date should not be a future date
        if (issuedDate > today) {
            ev.preventDefault();
            expiryDateInput.value = '';
           this.call("dialog", "add", AlertDialog, {
                title: "Validation Error",
                body: "Issue date should not be a future date.",
                className: "custom-alert-dialog",
            });
            return false;
        }
    }
});



publicWidget.registry.SubmitVendorFormValidation = publicWidget.Widget.extend({
    selector: 'form[action="/submit_vendor_registration"]',
    events: {
            'submit': '_onFormSubmit',
    },

    _onFormSubmit: function (ev) {
        ev.preventDefault();  // prevent default submit for processing

        const form = ev.currentTarget;
        const submitBtn = form.querySelector('button[type="submit"]');

        // If already disabled, don't allow another submit
        if (submitBtn.disabled) {
            return;
        }

        // Disable the button to prevent multiple submissions
        submitBtn.disabled = true;

        // Submit the form programmatically
        form.submit();
    }
});



publicWidget.registry.UnfoundBank = publicWidget.Widget.extend({
    selector: '.bank_checkbox',
    events: {
            'click': '_on_click_unfound',
    },

    _on_click_unfound: function (ev) {
    debugger;
//        ev.preventDefault();  // prevent default submit for processing
//
        const form = ev.currentTarget;
        const unfoundbank_checkbox = document.querySelector('input[name="bank_not_found"]');
        const inputField = document.getElementById('unregistered_bank_input');
        const bankSelect = document.getElementById('bank_id');

        if (unfoundbank_checkbox && inputField && bankSelect) {
            unfoundbank_checkbox.addEventListener('change', function () {

                const isChecked = this.checked;
                inputField.style.display = this.checked ? 'block' : 'none';
                 if (isChecked) {
                        bankSelect.value = '';
                        bankSelect.disabled = true;
                    } else {
                        inputField.values = '';
                        bankSelect.disabled = false;
                    }
            });

            // If the page reloads with checkbox checked (e.g. error)
            if (unfoundbank_checkbox.checked) {
                inputField.style.display = 'block';
                bankSelect.value = '';
                bankSelect.disabled = true;
            }else {
                inputField.values = '';
                inputField.style.display = 'none';
                bankSelect.disabled = false;
            }
        }
    },
});



publicWidget.registry.ScreenshotPDF = publicWidget.Widget.extend({
    selector: '.vrf_button',
    events: {
        'click': '_takeScreenshot',
    },

    _takeScreenshot: function(event) {
        event.preventDefault();
        debugger;

        const button = event.currentTarget;
        const originalText = button.textContent;
        button.textContent = 'Preparing PDF...';
        button.disabled = true;

        try {
            // Simple approach: Use browser's print functionality
            const printElement = document.querySelector('.print_vrf_class');
            this._printPage(printElement);
        } catch (error) {
            console.error('Error:', error);
            alert('Please use Ctrl+P to print or save as PDF');
        } finally {
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);
        }
    },

    _captureFormValues: function (element) {
    const clonedElement = element.cloneNode(true);
    const originalInputs = element.querySelectorAll('input, select, textarea');
    const clonedInputs = clonedElement.querySelectorAll('input, select, textarea');

    originalInputs.forEach((input, index) => {
        const clonedInput = clonedInputs[index];
        if (!clonedInput) return;

        const span = document.createElement('span');
        let value = '';

        if (input.type === 'checkbox') {
            value = input.checked ? '✓' : '✗';
        } else if (input.tagName === 'SELECT') {
            value = input.options[input.selectedIndex]?.text || '';
        } else if (input.type === 'date') {
            value = input.value || '';
        } else {
            value = input.value || '';
        }

        span.textContent = value;
        span.style.display = 'inline-block';
        span.style.minHeight = '18px';

        clonedInput.replaceWith(span);
    });

    return clonedElement;
},

    _printPage: function(printElement) {
        const elementWithValues = this._captureFormValues(printElement);

        const printCSS = `
            <style>
            @media print {
                body {
                    margin: 0;
                    padding: 25px;
                    font-family: "Arial", sans-serif;
                    font-size: 13px;
                    color: #000;
                }

                h1, h2, h3 {
                    font-weight: bold;
                    margin: 25px 0 10px;
                    padding-bottom: 5px;
                    border-bottom: 1px solid #aaa;
                }

                .print_vrf_class {
                    width: 100%;
                }

                 .noc_button .vendor_attachment {
                    display: none;
                }

                .section-title {
                    font-size: 16px;
                    font-weight: bold;
                    margin-top: 20px;
                    border-bottom: 1px solid #ccc;
                    padding-bottom: 4px;
                }

                .form-grid {
                    display: grid;
                    grid-template-columns: 200px 1fr;
                    row-gap: 8px;
                    column-gap: 20px;
                    margin-bottom: 20px;
                }

                .form-grid label {
                    font-weight: bold;
                    color: #333;
                }

                .form-grid .value {
                    border-bottom: 1px solid #ccc;
                    padding: 2px 4px;
                    min-height: 18px;
                }

                .table-section {
                    margin-top: 20px;
                }

                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }

                th, td {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #bbb;
                }

                .no-print, .vrf_button {
                    display: none !important;
                }

                .page-break {
                    page-break-before: always;
                }
            }
            </style>
        `;

        const printWindow = window.open('', '', 'width=1024,height=768');
        printWindow.document.write(`
            <html>
            <head>
                <title style="text-align:center; bold:true;"><h2>Vendor Registration jj</h2></title>
                ${printCSS}
            </head>
            <body>
                ${elementWithValues.outerHTML}
            </body>
            </html>
        `);

        printWindow.document.close();
        printWindow.onload = function () {
            printWindow.focus();
            printWindow.print();
            setTimeout(() => printWindow.close(), 1000);
        };
    },

});





publicWidget.registry.SubmitCustomerFormValidation = publicWidget.Widget.extend({
    selector: 'form[action="/submit_customer_registration"]',
    events: {
            'submit': '_onFormSubmit',
    },

    _onFormSubmit: function (ev) {
        ev.preventDefault();  // prevent default submit for processing

        const form = ev.currentTarget;
        const submitBtn = form.querySelector('button[type="submit"]');

        // If already disabled, don't allow another submit
        if (submitBtn.disabled) {
            return;
        }

        // Disable the button to prevent multiple submissions
        submitBtn.disabled = true;

        // Submit the form programmatically
        form.submit();
    }
});




publicWidget.registry.VendorNOCPrint = publicWidget.Widget.extend({
        selector: '.noc_button',  // Your Print NOC button class
        events: {
            'click': '_onPrintNOC',
        },

        _onPrintNOC: async function (ev) {
            ev.preventDefault();
            debugger;
            const bankId = document.querySelector('select[name="bank_id"]').value || '';
            const isUnregistered = document.querySelector('input[name="bank_not_found"]')?.checked;
            const bankName = '';
            debugger;
            if (bankId) {
                const bankName = await rpc("/get_bank_info", {
                    bank_id:bankId
                }).then(result => {
                debugger;
                    if (result) {
                        console.log("Bank Name:", result);
                        this.bankName = result
                        debugger;
                        // Proceed to inject values into your PDF/Print logic
                    } else {
                        console.warn("No bank found");
                    }
                }).catch(error => {
                    console.error("ORM call failed:", error);
                });

            }

             if (isUnregistered) {
                this.bankName = document.querySelector('input[name="unregistered_bank"]')?.value || '';
            }

            debugger;
            // 1. Extract values
            const values = {
                'account_name': document.querySelector('input[name="account_name"]').value || '',
                'account_number': document.querySelector('input[name="account_number"]').value || '',
                'bank_name': this.bankName || '',
                'branch_name': document.querySelector('input[name="bank_branch_name"]').value || '',
                'address': document.querySelector('input[name="bank_address"]').value || '',
                'iban': document.querySelector('input[name="iban"]').value || '',
                'swift_code': document.querySelector('input[name="swift_code"]').value || '',
//                'branch_code': document.querySelector('input[name="branch_code"]').value || '',
//                'currency': document.querySelector('select[name="currency_id"]').value || '',
                'sort_code': document.querySelector('input[name="sort_code"]').value || '',
            };
            debugger;

            // 2. Build formatted printable HTML like the Excel image
            const today = new Date().toLocaleDateString('en-GB');

            const printContent = `
                <html>
                    <head>
                        <title>NOC Document</title>
                        <style>
                            body { font-family: Arial, sans-serif; padding: 20px; }
                            .header, .footer { margin-bottom: 10px; }
                            .bold { font-weight: bold; }
                            table { border-collapse: collapse; width: 100%; margin-top: 10px; }
                            table td, table th { border: 1px solid black; padding: 8px; }
                            .center { text-align: center; }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <div class="row col-12">
                                <div  class="col-5" style="float:left;">
                                    <p>To<br>
                                    Finance Dept.<br>
                                    Gulf Trading & Refrigerating CO. L.L.C. (GULFCO)<br>
                                    Dubai - U.A.E.</p>

                                    <p class="bold">Sub : NOC to transfer due amounts to our Bank</p>
                                    <p>Dear Sir/Madam,</p>
                                    <p>We have no objection to transfer due amount to our Bank account detail as below.</p>
                                </div>
                                <div  class="col-6" style="float:left;">
                                    <p><span class="bold">Date:</span> ${today}</p>
                                </div>
                            </div>
                        </div>

                        <table>
                            <tr><th style="text-align:left;" colspan="2">Beneficiary Detail</th></tr>
                            <tr><td width='30%'>Name</td><td>${values.account_name}</td></tr>
                            <tr><td width='30%'>Address</td><td>${values.address}</td></tr>

                            <tr><th style="text-align:left;" colspan="2">Beneficiary Bank Detail</th></tr>
                            <tr><td width='30%'>Bank Name</td><td>${values.bank_name}</td></tr>
                            <tr><td width='30%'>Branch</td><td>${values.branch_name}</td></tr>
                            <tr><td width='30%'>IBAN</td><td>${values.iban}</td></tr>
                            <tr><td width='30%'>SWIFT Code</td><td>${values.swift_code}</td></tr>
                            <tr><td width='30%'>Sort Code/IFSC Code:</td><td>${values.sort_code}</td></tr>
                        </table>

                        <div class="footer">
                            <p>Thanks & Best Regards,</p>
                            <p><br>Name<br>Designation<br>Signature<br>Seal</p>
                        </div>

                        <script>
                            window.onload = function() {
                                window.print();
                            };
                        </script>
                    </body>
                </html>
            `;

            // 3. Open new window and write content
            const printWindow = window.open('', '_blank');
            printWindow.document.open();
            printWindow.document.write(printContent);
            printWindow.document.close();
        }
    });






publicWidget.registry.VendorTradeLicenseValidation = publicWidget.Widget.extend({
    selector: '.vendor_trade_license',
    events: {
        'blur input[name="trade_license_no"]': '_onTradeLicenseBlur',
    },


     _onTradeLicenseBlur: async function (ev) {
        const $input = $(ev.currentTarget);
        const tradeLicense = $input.val().trim();
//        debugger;
        if (!tradeLicense) return;

        try {
            const result = await rpc('/portal/trade_license/check', {
                tr: tradeLicense,
            });

            if (result.exists) {
                // Show popup or inline warning
                alert("⚠️ This Trade License is already used!");

                // Optional: clear input and focus again
                $input.val('').focus();
            }
        } catch (error) {
            console.error("Trade License check failed:", error);
        }
    },

});


publicWidget.registry.CustomerTradeLicenseValidation = publicWidget.Widget.extend({
    selector: '.customer_trade_license',
    events: {
        'blur input[name="trade_license"]': '_onCustomerTradeLicenseBlur',
    },


     _onCustomerTradeLicenseBlur: async function (ev) {
        const $input = $(ev.currentTarget);
        const tradeLicense = $input.val().trim();
//        debugger;
        if (!tradeLicense) return;

        try {
            const result = await rpc('/portal/trade_license/check', {
                tr: tradeLicense,
            });

            if (result.exists) {
                // Show popup or inline warning
                alert("⚠️ This Trade License is already used!");

                // Optional: clear input and focus again
                $input.val('').focus();
            }
        } catch (error) {
            console.error("Trade License check failed:", error);
        }
    },

});