odoo.define('ag_admission_custom.batch_on_courses', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require("web.Dialog");
    var session = require('web.session');
    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var publicWidget = require('web.public.widget');
    var utils = require('web.utils');
    var _t = core._t;
    var qweb = core.qweb;
    //var SubjectSelection = require('openeducat_core_enterprise.batch_on_courses');
    publicWidget.registry.SubjectRegister.include({
        events: {
            'click button[type="submit"]': '_onFormSubmit',
            
            'change select[name="elective_subject_ids"]': '_onChangeElective',
            'change select[name="compulsory_subject_ids"]': '_onChangeComp',
            'change select[name="term_ids"]': '_onchangedropdown',
            'change select[name="session_ids"]': '_onChangeSession',
            // 'change select[name="batch_id"]': '_onChangeBatch',
            'change #batch_on_courses': '_onChangeBatch',
            'change #course_dropdown': '_onchangedropdown',
        },
        xmlDependencies: ['/openeducat_core_enterprise/static/src/xml/custom.xml'],

        start: function(){
              var res = this._super();
                $(".js-example-basic-multiple").select2();
                this._getTotal();
                this._getTotalCost();
                this._getmincredit();
                this._getmaxcredit();
                this._getelectivity();
                this._getcompulsory();
                
                this._getterm();
                this._getacadmic();
                // $("div.terms").hide();
                return res;
        },

        _onChangeComp: function(){
            this._getTotal();
            this._getTotalCost();
            this._getSession();
            // var result = {};
            // var compulsory_subject_ids = [];
            
            // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
            // result['compulsory_subject_ids'] = compulsory_subject_ids
            
            // var comp = compulsory_subject_ids[compulsory_subject_ids.length - 1];
            // var comps = compulsory_subject_ids;
            // delete comps[compulsory_subject_ids.length - 1];
            // var comps = compulsory_subject_ids - compulsory_subject_ids[compulsory_subject_ids.length - 1]
            // console.log(comps)
            // ajax.jsonRpc('/get/subject/subcredit', 'call',result).then( function(res){
            //     var min = $('input[name="min_credit"]').val()
            //     var max = $('input[name="max_credit"]').val()
            //     console.log(res);
            //     console.log(min);
            //     console.log(max);
            //     if (parseInt(res) < parseInt(min) || parseInt(res) > parseInt(max)){
            //         alert("Credit of this subject of range of this course!!");
            //         // var x = document.getElementById("comp_list");  
            //         // x.remove(x.selectedIndex);  
            //         // $("select[name='compulsory_subject_ids']").val(comps);
            //     }
            // });
            // ajax.jsonRpc('/check/birthdate', 'call',
            //         {
            //         'birthdate': formattedDate,
            //         'register': register_id,
            //         }).then(function (data) {
            //         if (data['birthdate'])
            //         {
            //           alert('Not Eligible for Admission minimum required age is :'+ data['age']);
            //           var birth_date = $("input[name='birth_date']").val('');
            //         }
            //         });
            
            // self._getmincredit();
            // self._getmaxcredit();
            // self._getcompulsory();
        },

        _onChangeElective: function(){
            this._getTotal();
            this._getTotalCost();
            this._getSession();
            // self._getmincredit();
            // self._getmaxcredit();
        },
        _onChangeBatch: function(){
            // this._getTotal();
            // this._getmincredit();
            // this._getmaxcredit();
            console.log('***********************************************')
            this._getmincredit();
            this._getmaxcredit();
            this._getelectivity();
            this._getcompulsory();
            
            // this._getterm();
            // this._getacadmic();
        },

        _onChangeCourse: function(){
            this._getTotal();
            this._getTotalCost();
            
            // this._getcompulsory();
            // this._getelectivity();
            this._getterm();
            this._getacadmic();
        },
        _onChangeSession: function(){
            this._getTotal();
            this._getTotalCost();
            this._getSession();
            this._getSessions();
        },

        _onchangedropdown: function(){
            var self = this;
            var course_id = $("#course_dropdown").val();
            var batch = $("#batch_on_courses").find('option:selected').val();
            console.log(course_id);
            ajax.jsonRpc('/get/course_data', 'call',
                {
                'course_id': course_id,
                'term_ids': $('select[name="term_ids"]').val(),
                }).then(function (data) {
                if (data)
                {
                var batch_data = qweb.render('GetBatchData',
                {
                    batches: data['batch_list'],

                });
                $('.batches').html(batch_data);
                if(batch){
                    if($("#batch_on_courses").find('option[value="' + batch + '"]').length){
                        $("#batch_on_courses").find('option[value="' + batch + '"]').attr('selected', 'selected')
                    }
                }
                if(data)
                var subject_data = qweb.render('GetSubjectData',
                {
                    subjects: data['subject_list']
                });
                $('.subjects').html(subject_data);

                }
                self._getTotal();
                self._getTotalCost();
                self._getmincredit();
                self._getmaxcredit();
                // self._getelectivity();
                // self._getcompulsory();
                
                self._getterm();
                self._getacadmic();
                });
        },

        _getTotal: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                var elective_subject_ids = [];
                var compulsory_subject_ids = [];
                $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                result['compulsory_subject_ids'] = compulsory_subject_ids
                result['elective_subject_ids'] = elective_subject_ids
                result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/total', 'call',result).then( function(res){
                    $('input[name="total_credit"]').val(res);
                });
            }
        },
        _getTotalCost: function(){
            var result = {};
            if($('select[name="session_ids"]').val()){

                var session_ids = [];
                $("select[name='session_ids']").select2('data').forEach( element => session_ids.push(parseInt(element.id)))
                result['session_ids'] = session_ids
                console.log(session_ids);
                return ajax.jsonRpc('/get/subject/totalcost', 'call',result).then( function(res){
                    $('input[name="total_cost"]').val(res);
                });
            }
        },
        _getmincredit: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                result['batch_ids'] = $('select[name="batch_id"]').val()
                return ajax.jsonRpc('/get/subject/mincredit', 'call',result).then( function(res){
                    $('input[name="min_credit"]').val(res);
                });
            }
        },
        _getmaxcredit: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                result['batch_ids'] = $('select[name="batch_id"]').val()
                return ajax.jsonRpc('/get/subject/maxcredit', 'call',result).then( function(res){
                    $('input[name="max_credit"]').val(res);
                });
            }
        },
        _getcompulsory: function(){
            var result = {};
            if($('select[name="batch_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['batch_id'] = $('select[name="batch_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/compulsory', 'call',result).then( function(res){
                    $('select[name="compulsory_subject_ids"]').empty().append(res);
                });
            }
        },
        _getelectivity: function(){
            var result = {};
            if($('select[name="batch_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['batch_id'] = $('select[name="batch_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/electivity', 'call',result).then( function(res){
                    $('select[name="elective_subject_ids"]').empty().append(res);
                });
            }
        },
        _getSession: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                var elective_subject_ids = [];
                var compulsory_subject_ids = [];
                var session_ids = [];
                $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                $("select[name='session_ids']").select2('data').forEach( element => session_ids.push(parseInt(element.id)))
                result['compulsory_subject_ids'] = compulsory_subject_ids
                result['session_ids'] = session_ids
                console.log(session_ids);
                console.log(compulsory_subject_ids);
                console.log(elective_subject_ids);
                result['elective_subject_ids'] = elective_subject_ids
                result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/gensession', 'call',result).then( function(res){
                    $('select[name="session_ids"]').empty().append(res);
                });
            }
        },
        _getSessions: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                var elective_subject_ids = [];
                var compulsory_subject_ids = [];
                var session_ids = [];
                $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                $("select[name='session_ids']").select2('data').forEach( element => session_ids.push(parseInt(element.id)))
                result['compulsory_subject_ids'] = compulsory_subject_ids
                result['session_ids'] = session_ids
                console.log(session_ids);
                console.log(compulsory_subject_ids);
                console.log(elective_subject_ids);
                result['elective_subject_ids'] = elective_subject_ids
                result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/gensessions', 'call',result).then( function(res){
                    $('select[name="session_ids2"]').val(res);
                });
            }
        },
        _getterm: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                // result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/getterm', 'call',result).then( function(res){
                    $('select[name="term_ids"]').val(res);
                });
            }
        },
        _getacadmic: function(){
            var result = {};
            if($('select[name="course_id"]').val()){

                // var elective_subject_ids = [];
                // var compulsory_subject_ids = [];
                // $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
                // $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
                // result['compulsory_subject_ids'] = compulsory_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                // result['elective_subject_ids'] = elective_subject_ids
                result['course_id'] = $('select[name="course_id"]').val()
                result['term_ids'] = $('select[name="term_ids"]').val()
                return ajax.jsonRpc('/get/subject/getacadmic', 'call',result).then( function(res){
                    $('select[name="year_ids"]').val(res);
                });
            }
        },
        _onFormSubmit: function(e){
            e.preventDefault();
            var result = { };
            $.each($('form').serializeArray(), function() {
                result[this.name] = this.value;
            });
            var elective_subject_ids = []
            var compulsory_subject_ids = []
            $("select[name='elective_subject_ids']").select2('data').forEach( element => elective_subject_ids.push(parseInt(element.id)))
            $("select[name='compulsory_subject_ids']").val().forEach( element => compulsory_subject_ids.push(parseInt(element)))
            result['compulsory_subject_ids'] = compulsory_subject_ids
            result['elective_subject_ids'] = elective_subject_ids
            result['max_hours'] = $('input[name="max_credit"]').val()
            result['min_hours'] = $('input[name="min_credit"]').val()
            ajax.jsonRpc('/subject/registration/check', 'call', result).then( function(res){
                console.log(result)
                if(res == false){
                    $('form').submit()
                } else {
                    alert(res);
                }
            });
        }
    });
//    websiteRootData.websiteRootRegistry.add(SubjectSelection, '.js_get_data');

});