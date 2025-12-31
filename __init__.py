# -*- coding: utf-8 -*-
#
# Removes the field formatting of all selected notes.
#
# Original author: Felix Esch
# Updated to 25.02.5 by FlaccidSnake using Claude AI
# Licence: GNU General Public Licence (GNU GPL), version 3

from PyQt6.QtGui import QAction
from anki.hooks import addHook
from aqt import mw
import re


def stripFormatting(txt):
    """
    Removes all html tags, except if they begin like this: <img...>
    This allows inserted images to remain.
    
    Parameters
    ----------
    txt : string
        the string containing the html tags to be filtered
    
    Returns
    -------
    string
        the modified string as described above
    """
    return re.sub("<(?!img).*?>", "", txt)


def setupMenu(browser):
    """
    Add the button to the browser menu "edit".
    """
    a = QAction("Bulk-Clear Formatting", browser)
    a.triggered.connect(lambda: onClearFormatting(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)


def onClearFormatting(browser):
    """
    Clears the formatting for every selected note.
    Also creates a restore point, allowing a single undo operation.
    
    Parameters
    ----------
    browser : Browser
        the anki browser from which the function is called
    """
    mw.checkpoint("Bulk-Clear Formatting")
    mw.progress.start()
    
    for nid in browser.selectedNotes():
        note = mw.col.getNote(nid)
        
        def clearField(field):
            result = stripFormatting(field)
            # if result != field:
            #     print(f"Changed: \"{field}\" ==> \"{result}\"")
            return result
        
        note.fields = [clearField(field) for field in note.fields]
        note.flush()
    
    mw.progress.finish()
    mw.reset()


addHook("browser.setupMenus", setupMenu)
