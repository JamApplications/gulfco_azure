odoo.define('ag_admission_custom.student_registration', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require("web.Dialog");
    var session = require('web.session');
    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var publicWidget = require('web.public.widget');
    var websiteRootData = require('website.root');
    var utils = require('web.utils');
    var field_utils = require('web.field_utils');
    var _t = core._t;
    var qweb = core.qweb;
    var currentTab = 1; 
    const time = require('web.time');
    publicWidget.registry.student_register.include({
    // publicWidget.registry.student_register = publicWidget.Widget.extend({
        selector: '.js_get_data',
        events:{
                'click #nextBtn': '_onFormSubmit',
                'click #prevBtn': '_onFormSubmits',
                'change #self_application': '_onchangedropdown',
                'change .admission_form_date': '_onchangebirthdate',
                'change .jobdetals': '_oncurrentlywork',
                'change .casestype': '_oncasestype',},

        xmlDependencies: ['/openeducat_online_admission/static/src/xml/custome.xml','/jam_grading/views/admission_website.xml'],
        init: function(){
            this._super.apply(this,arguments);
        },
        _oncasestype: function(){
            // console.log($("#yes").val());
            // console.log($("#no").val());
            // console.log($("select[name='case_type']").val());
            if (String($("select[name='case_type']").val()) === 'transfer'){
                $("div.transfers").show();
                $("div.citizen").hide();
                $("div.faculties").hide();
                $("div.qosors").hide();
            }
            else if (String($("select[name='case_type']").val()) === 'son of citizen'){
                $("div.transfers").hide();
                $("div.citizen").show();
                $("div.faculties").hide();
                $("div.qosors").hide();}
            else if (String($("select[name='case_type']").val()) === 'son of faculty'){
                $("div.transfers").hide();
                $("div.citizen").hide();
                $("div.faculties").show();
                $("div.qosors").hide();}
            else if (String($("select[name='case_type']").val()) === 'son of qosor'){
                $("div.transfers").hide();
                $("div.citizen").hide();
                $("div.faculties").hide();
                $("div.qosors").show();}
            else {
                $("div.transfers").hide();
                $("div.citizen").hide();
                $("div.faculties").hide();
                $("div.qosors").hide();}
        },
        _oncurrentlywork: function(){
            // console.log($("#yes").val());
            // console.log($("#no").val());
            // console.log($("input[name='currently_work']:checked").val());
            if (String($("input[name='currently_work']:checked").val()) === 'False'){
                $("div.job_detail").hide();
            }
            else{
            $("div.job_detail").show();}
        },
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then( function(){
                $("#birthdate").attr('placeholder', time.getLangDateFormat());
                $( "#birthdate" ).datepicker('destroy');
                $( ".admission_form_date" ).each( function(){
                    self._initDateTimePicker($(this));
                });
                $( ".admission_end_date" ).each( function(){
                    self._initEndDateTimePicker($(this));
                });
                // $("div.job_detail").hide();
                // if ($("div.job_detail").val() === 'True'){
                //     $("div.job_detail").show();
                // }
                $("div.job_detail").hide();
                $("div.transfers").hide();
                $("div.citizen").hide();
                $("div.faculties").hide();
                $("div.qosors").hide();
                // $( ".job_detail" ).each( function(){
                //     self._initEndDateTimePicker($(this));
                // });
            });

        },
        _formatDate: function(){
            var dateFormat = time.getLangDateFormat();
            var formatArr = ['Y','M','D'];
            for(var idx in formatArr){
                var chr =  formatArr[idx];
                var count = [...dateFormat].filter(x => x === chr).length;
                if(count > 2){
                    dateFormat = dateFormat.replace( `${chr.repeat(count)}`, `${chr.repeat(2)}` );
                }
            }
            dateFormat = dateFormat.toLowerCase()
            return dateFormat;
        },

        _initDateTimePicker: function ($dateGroup) {
            var self = this;
            var datetimepickerFormat = time.getLangDateFormat();
            $dateGroup.datetimepicker({
                format : datetimepickerFormat,
                minDate: 0,
                useCurrent: false,
                maxDate: moment(new Date()),
                viewDate: false,
                icons: {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    next: 'fa fa-chevron-right',
                    previous: 'fa fa-chevron-left',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down',
                },
                locale : moment.locale(),
                allowInputToggle: true,
            });
            $dateGroup.on('change.datetimepicker', function(ev){
                self._onchangebirthdate(ev);
            })
        },
        _initEndDateTimePicker: function ($dateGroup) {
            var self = this;
            var datetimepickerFormat = time.getLangDateFormat();
            $dateGroup.datetimepicker({
                format : datetimepickerFormat,
                minDate: 0,
                useCurrent: false,
                // maxDate: moment(new Date()),
                viewDate: false,
                icons: {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    next: 'fa fa-chevron-right',
                    previous: 'fa fa-chevron-left',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down',
                },
                locale : moment.locale(),
                allowInputToggle: true,
            });
            $dateGroup.on('change.datetimepicker', function(ev){
                self._onchangebirthdate(ev);
            })
        },

        _onchangedropdown: function(ev){
            var application = $(ev.currentTarget).val();
            ajax.jsonRpc('/get/application_data', 'call',
                {
                'application': application,
                }).then(function (data) {
                if (data['student_id'])
                {
                var student_data = qweb.render('GetStudentData',
                {
                    students: data['student_id'][0],
                    country: data['country_id']
                });
                $('.students').html(student_data);
                $('.country').html(student_data);
                }
                else if (data['country'])
                {
                  var others_data = qweb.render('GetOthersData',
                {
                    others: data['country'],
                });
                $('.others').html(others_data);
                }

            });
        },

        _onchangebirthdate: function(ev){
            var birth_date = $("input[name='birth_date']").val();
            var register_id = $("select[name='register_id']").val();
            var momentDate = field_utils.parse.date(birth_date);
            var formattedDate = momentDate ? momentDate.toJSON() : '';
            if(register_id){
                ajax.jsonRpc('/check/birthdate', 'call',
                    {
                    'birthdate': formattedDate,
                    'register': register_id,
                    }).then(function (data) {
                    if (data['birthdate'])
                    {
                      alert('Not Eligible for Admission minimum required age is :'+ data['age']);
                      var birth_date = $("input[name='birth_date']").val('');
                    }
                    });
            }
            else{
                alert('Please Select a Program grading');
                var birth_date = $("input[name='birth_date']").val('');
            }
        },
        _onFormSubmit: function(e){
            e.preventDefault();
            console.log('gggggggggggggggggggggggggggg')
            console.log(document.getElementById("nextBtn").innerHTML)
            var x = document.getElementsByClassName("tab");
            if (currentTab <= x.length) {currentTab = currentTab + 1;}
            console.log(currentTab);
            var result = { };
            result['score'] = $('input[name="score"]').val()
            result['country_id'] = $('select[name="nationality"]').val()
            if (currentTab > x.length) {
                ajax.jsonRpc('/addmisregistration/check', 'call', result).then( function(res){
                    console.log(result)
                    if(res == false){
                        $('form').submit()
                    } else {
                        alert(res);
                    }
                });
            }
        },
        _onFormSubmits: function(e){
            e.preventDefault();
            // console.log('gggggggggggggggggggggggggggg')
            // console.log(document.getElementById("nextBtn").innerHTML)
            // var x = document.getElementsByClassName("tab");
            var x = document.getElementsByClassName("tab");
            if (currentTab > x.length) {
                currentTab = currentTab - 2;
            }
            else{
            currentTab = currentTab - 1;}
            // var result = { };
            // result['score'] = $('input[name="score"]').val()
            // result['country_id'] = $('select[name="nationality"]').val()
            // if (currentTab == x.length) {
            //     ajax.jsonRpc('/addmisregistration/check', 'call', result).then( function(res){
            //         console.log(result)
            //         if(res == false){
            //             $('form').submit()
            //         } else {
            //             alert(res);
            //         }
            //     });
            // }
        }
    });

    return publicWidget.registry.student_register;
});
