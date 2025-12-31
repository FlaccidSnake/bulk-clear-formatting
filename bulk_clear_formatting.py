# -*- coding: utf-8 -*-
#
# Removes the field formatting of all selected notes.
#
# Author: Felix Esch
# Updated for Anki 25.02.5 with UI
# VCS+issues: https://github.com/Araeos/ankiplugins
# Licence: GNU General Public Licence (GNU GPL), version 3

from typing import List, Optional, Sequence, cast
import re

from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QCheckBox,
)
from anki.hooks import addHook
from anki.notes import NoteId
from aqt import mw
from aqt.utils import tooltip, askUser
from aqt.browser.browser import Browser


def stripFormatting(txt, preserve_br=False):
    """
    Removes all html tags, except if they begin like this: <img...>
    This allows inserted images to remain.
    
    Parameters
    ----------
    txt : string
        the string containing the html tags to be filtered
    preserve_br : bool
        if True, preserves <br> and <br/> tags
    
    Returns
    -------
    string
        the modified string as described above
    """
    if preserve_br:
        # Exclude img and br tags from removal
        return re.sub("<(?!img|br).*?>", "", txt)
    else:
        return re.sub("<(?!img).*?>", "", txt)


class ClearFormattingDialog(QDialog):
    """Dialog for selecting which field to clear formatting from"""
    
    def __init__(self, browser: Browser, nids: Sequence[NoteId]):
        super().__init__(parent=browser)
        self._browser = browser
        self._nids = nids
        
        # Get fields from the first selected note
        fields = self.get_fields()
        if fields is None:
            from aqt.utils import showCritical
            showCritical("Error: Could not determine note type of selected notes", parent=self)
            self.close()
            return
        
        # Setup UI
        self.setWindowTitle("Clear Formatting")
        self.setMinimumWidth(400)
        
        # Main layout
        vbox = QVBoxLayout()
        
        # Field selector
        field_label = QLabel("Clear formatting in field:")
        self.field_selector = QComboBox()
        self.field_selector.addItems(fields)
        
        field_hbox = QHBoxLayout()
        field_hbox.addWidget(field_label)
        field_hbox.addWidget(self.field_selector)
        field_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # "All fields" checkbox
        self.checkbox_all = QCheckBox("Clear formatting in ALL fields")
        self.checkbox_all.setChecked(False)
        self.checkbox_all.stateChanged.connect(self.on_checkbox_changed)
        
        # "Preserve line breaks" checkbox
        self.checkbox_preserve_br = QCheckBox("Preserve line breaks (<br> tags)")
        self.checkbox_preserve_br.setChecked(False)
        
        # Buttons
        button_box = QDialogButtonBox(Qt.Orientation.Horizontal, self)
        clear_button = cast(
            QPushButton,
            button_box.addButton("Clear Formatting", QDialogButtonBox.ButtonRole.AcceptRole)
        )
        cancel_button = cast(
            QPushButton,
            button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        )
        
        clear_button.clicked.connect(self.on_confirm)
        cancel_button.clicked.connect(self.close)
        
        # Add widgets to layout
        vbox.addLayout(field_hbox)
        vbox.addWidget(self.checkbox_all)
        vbox.addWidget(self.checkbox_preserve_br)
        vbox.addWidget(button_box)
        
        self.setLayout(vbox)
    
    def get_fields(self) -> Optional[List[str]]:
        """Get field names from the first selected note"""
        if not self._nids:
            return None
        nid = self._nids[0]
        note = mw.col.get_note(nid)
        model = note.note_type()
        if model is None:
            return None
        fields = mw.col.models.field_names(model)
        return fields
    
    def on_checkbox_changed(self, state):
        """Enable/disable field selector based on checkbox"""
        self.field_selector.setEnabled(not self.checkbox_all.isChecked())
    
    def on_confirm(self):
        """Execute the formatting clear operation"""
        clear_all = self.checkbox_all.isChecked()
        preserve_br = self.checkbox_preserve_br.isChecked()
        field_name = self.field_selector.currentText() if not clear_all else None
        
        # Confirmation dialog
        if clear_all:
            q = (
                f"This will clear formatting in <b>ALL fields</b> "
                f"of <b>{len(self._nids)} selected note(s)</b>. Proceed?"
            )
        else:
            q = (
                f"This will clear formatting in the <b>'{field_name}'</b> field "
                f"of <b>{len(self._nids)} selected note(s)</b>. Proceed?"
            )
        
        if not askUser(q, parent=self):
            return
        
        # Perform the operation
        mw.checkpoint("Clear Formatting")
        mw.progress.start()
        
        count = 0
        for nid in self._nids:
            note = mw.col.get_note(nid)
            
            if clear_all:
                # Clear all fields
                for i, field in enumerate(note.fields):
                    result = stripFormatting(field, preserve_br)
                    if result != field:
                        note.fields[i] = result
                        count += 1
            else:
                # Clear specific field
                field_names = mw.col.models.field_names(note.note_type())
                if field_name in field_names:
                    field_index = field_names.index(field_name)
                    result = stripFormatting(note.fields[field_index], preserve_br)
                    if result != note.fields[field_index]:
                        note.fields[field_index] = result
                        count += 1
            
            note.flush()
        
        mw.progress.finish()
        mw.reset()
        
        # Close dialog and show tooltip
        self.close()
        if clear_all:
            tooltip(f"<b>Cleared formatting</b> in {len(self._nids)} note(s).", parent=self._browser)
        else:
            tooltip(f"<b>Cleared formatting</b> in '{field_name}' field of {len(self._nids)} note(s).", parent=self._browser)


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
    Opens the dialog to clear formatting for selected notes.
    
    Parameters
    ----------
    browser : Browser
        the anki browser from which the function is called
    """
    nids = browser.selectedNotes()
    if not nids:
        tooltip("No notes selected.", parent=browser)
        return
    
    dialog = ClearFormattingDialog(browser, nids)
    dialog.exec()


addHook("browser.setupMenus", setupMenu)


##############################################################################
###### Browser Context Menu (Right-click on notes/cards in browser)

def add_to_browser_context(browser, menu):
    """Add clear formatting option to browser right-click menu"""
    nids = browser.selectedNotes()
    if not nids:
        return
    
    # Add separator for visual grouping
    menu.addSeparator()
    
    # Add the clear formatting action
    a = menu.addAction("Clear Formatting...")
    a.triggered.connect(lambda: onClearFormatting(browser))

addHook("browser.onContextMenu", add_to_browser_context)


##############################################################################
###### Editor Context Menu (Right-click in note editor)

def add_to_editor_context(view, menu):
    """Add clear formatting option to editor right-click menu"""
    e = view.editor
    if not e or not e.note:
        return
    
    # Add separator for visual grouping
    menu.addSeparator()
    
    # Get current field
    field = e.currentField
    if field is not None:
        # Get field name
        field_names = mw.col.models.field_names(e.note.note_type())
        if field < len(field_names):
            field_name = field_names[field]
            
            # Add "Clear Formatting in This Field" option
            a = menu.addAction(f"Clear Formatting in '{field_name}'")
            a.triggered.connect(lambda: clear_current_field(e, field, field_name))
    
    # Add "Clear Formatting in All Fields" option
    a = menu.addAction("Clear Formatting in All Fields")
    a.triggered.connect(lambda: clear_all_fields_editor(e))

addHook("EditorWebView.contextMenuEvent", add_to_editor_context)


def clear_current_field(editor, field_index, field_name):
    """Clear formatting in the current field"""
    if not editor.note:
        return
    
    note = editor.note
    original = note.fields[field_index]
    # Always preserve <br> in editor context menu (safer default)
    cleaned = stripFormatting(original, preserve_br=True)
    
    if cleaned == original:
        tooltip(f"No formatting to clear in '{field_name}'", parent=editor.widget)
        return
    
    note.fields[field_index] = cleaned
    editor.loadNoteKeepingFocus()
    tooltip(f"Cleared formatting in '{field_name}'", parent=editor.widget)


def clear_all_fields_editor(editor):
    """Clear formatting in all fields of the current note"""
    if not editor.note:
        return
    
    note = editor.note
    changed = False
    
    for i, field in enumerate(note.fields):
        # Always preserve <br> in editor context menu (safer default)
        cleaned = stripFormatting(field, preserve_br=True)
        if cleaned != field:
            note.fields[i] = cleaned
            changed = True
    
    if not changed:
        tooltip("No formatting to clear", parent=editor.widget)
        return
    
    editor.loadNoteKeepingFocus()
    tooltip("Cleared formatting in all fields", parent=editor.widget)
