# -*- coding: utf-8 -*-
#!/usr/bin/python

import hal
import glib
import time
import gtk

class HandlerClass:
    '''
    class with gladevcp callback handlers
    '''

    def on_cmbMillType_changed(self,widget,data=None):
        '''
        a callback method
        parameters are:
            the generating object instance, likte a GtkButton instance
            user data passed if any - this is currently unused but
            the convention should be retained just in case
        '''
        print "*** on_cmbMillType_changed"
        
        image_list = ["diagonal.png", "diagonalRL.png",
            "perforation.png", "transverse.png", "cone.png"]
            
        control_list = ["diagonal", "diagonalRL", "perforation",
        "transverse", "cone"] # порядок типов фрезеровки в conbobox
        
        active_control_list = {"diagonal":["spnWD", "spnWd", "spn_alpha",
                        "spnS", "spn_d", "spn_p2"],
             "diagonalrl":["spnWD", "spnWd", "spn_alpha",
                        "spnS", "spn_d", "spn_p2"],
             "perforation":["spnS", "spn_d"],
             "transversal":["spnWD", "spnWd","spnS", "spn_d", "spn_p2"],
             "cone":["spnS", "spn_d", "spnD"],
             "all":["spnWD", "spnWd", "spn_d", "spn_alpha",
             "spnS", "spn_p2", "spnD"]
             } # список элементов управления, активных для пазов разной формы
             
        cmbMillType = self.builder.get_object('cmbMillType')
        item = cmbMillType.get_active_iter()
        if item is not None:
            imgDrawing = self.builder.get_object('imgDrawing')
            model = cmbMillType.get_model()
            index = model[item]
            print "***", index[0] , " *** ", index[1], " *** ", index[2]
            i = index[1]
            print "*** i = ", i 
            #pixbuf = gtk.gdk.new_from_file_at_scale(image_list[i], 400, 800, True)
            #pixbuf = gtk.gdk.GdkPixbuf.Pixbuf.new_from_file_at_scale(image_list[i], 400, 800, True)
            #pixbuf = gtk.gdk.Pixbuf.new_from_file_at_scale(image_list[i], 400, 800, True)
            #imgDrawing = imgDrawing.set_from_pixbuf(pixbuf)
            
            imgDrawing = imgDrawing.set_from_file(image_list[i])
            
            for control_name in active_control_list["all"]:
                self.builder.get_object(control_name).set_sensitive(False)
            for control_name in active_control_list[index[2]]:
                self.builder.get_object(control_name).set_sensitive(True)
        #self.nhits += 1
        #self.builder.get_object('hits').set_label("Hits: %d" % (self.nhits))
    
    def on_btnSave_clicked(self,widget):
        window1 = self.builder.get_object('window1')
        "spnNumber"
        "spn_alpha"
        
        "spnLength"
        "wpnWidth"
        "spnWd"
        "spnWD"
        "spn_d"
        "spnD"
        "spnS"
        "spn_p2"
        #чтение шаблона
        f1 = open("Сверление с комментариями.ngc",'rb')
        filedata1 = f1.read()
        f1.close()
        
        print "\nФайл 1\n=========================="
        print filedata1
        
        f2 = open("Фрезерование паза с комментриями.ngc",'rb')
        filedata2 = f2.read()
        f2.close()
        
        print "\nФайл 2\n=========================="
        print filedata2
        #["Сверление с комментариями.ngc", "Фрезерование паза с комментриями.ngc"]
        #замена
        replacements = [["#<_i>",],
            ["#<_N>",],
            ["#<_alpha>",],
            ["#<_beta>",],
            ["#<_beta>",],
            ["#<_F>",]]
        
        #https://python-gtk-3-tutorial.readthedocs.io/en/latest/dialogs.html
        #https://github.com/cnc-club/linuxcnc-features/blob/master/features.py
        filechooserdialog = gtk.FileChooserDialog(
            "Сохранить файл программы", window1,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OK, gtk.RESPONSE_OK))#, action=gtk.FileChooserAction.OPEN
        
        try :
            filt = gtk.FileFilter()
            filt.set_name("NGC")
            filt.add_mime_type("text/ngc")
            filt.add_pattern("*.ngc")
            filechooserdialog.add_filter(filt)
            #filechooserdialog.set_current_folder(APP_PATH + NGC_DIR)

            response = filechooserdialog.run()
            print "***response = ", response
            if response == gtk.RESPONSE_OK:
                #gcode = self.to_gcode()
                filename = filechooserdialog.get_filename()
                if filename[-4] != ".ngc" not in filename :
                    filename += ".ngc"
                #f = open(filename, "w")
                #f.write(gcode)
                print "*** filename = ", filename 
            #f.close()
        finally :
            filechooserdialog.destroy()
        
        #for replacement in replacements:
        #    filedata = filedata.replace(replacement[0], replacement[1])
        #    
        ##диалог выбора названия файла
        #
        ##создание и запись нового файла
        #configfile = codecs.open(self.NAME,'ab+','utf-8')
        #config.write(configfile)
        #configfile.close()
        pass

    def __init__(self, halcomp,builder,useropts):
        '''
        Handler classes are instantiated in the following state:
        - the widget tree is created, but not yet realized (no toplevel window.show() executed yet)
        - the halcomp HAL component is set up and the widhget tree's HAL pins have already been added to it
        - it is safe to add more hal pins because halcomp.ready() has not yet been called at this point.

        after all handlers are instantiated in command line and get_handlers() order, callbacks will be
        connected with connect_signals()/signal_autoconnect()

        The builder may be either of libglade or GtkBuilder type depending on the glade file format.
        '''

        self.halcomp = halcomp
        self.builder = builder
        self.nhits = 0


def get_handlers(halcomp,builder,useropts):
    '''
    this function is called by gladevcp at import time (when this module is passed with '-u <modname>.py')

    return a list of object instances whose methods should be connected as callback handlers
    any method whose name does not begin with an underscore ('_') is a  callback candidate

    the 'get_handlers' name is reserved - gladevcp expects it, so do not change
    '''
    return [HandlerClass(halcomp,builder,useropts)]
