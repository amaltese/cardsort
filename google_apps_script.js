/*
 * Card Sort private Google storage bridge.
 *
 * Paste this entire file into https://script.google.com while signed in to
 * the Google account that owns your Card Sort Sheet and Audio recordings
 * folder. Replace the three placeholder values below before deploying.
 */

const SPREADSHEET_ID = 'PASTE_YOUR_CARD_SORT_DATA_SHEET_ID_HERE';
const AUDIO_FOLDER_ID = 'PASTE_YOUR_AUDIO_RECORDINGS_FOLDER_ID_HERE';
const API_SECRET = 'PASTE_A_LONG_RANDOM_SECRET_HERE';

const TABLES = {
  studies: ['study_id', 'token', 'title', 'description', 'instructions', 'researcher_info', 'condition', 'item_label', 'allow_new_categories', 'allow_rename_categories', 'allow_delete_categories', 'allow_category_descriptions', 'allow_unassigned', 'require_all_placed', 'log_interactions', 'category_order', 'reflection_questions_json', 'created_at', 'updated_at'],
  cards: ['card_id', 'study_id', 'title', 'description', 'example', 'researcher_notes', 'display_order', 'active', 'color_fill', 'color_text', 'color_border'],
  categories: ['category_id', 'study_id', 'name', 'description', 'display_order', 'color_fill', 'color_text', 'color_border'],
  participant_sessions: ['session_token', 'study_id', 'status', 'completion_code', 'started_at', 'completed_at', 'snapshot_json'],
  card_placements: ['placement_id', 'session_token', 'card_id', 'category_name', 'card_order', 'updated_at'],
  reflection_responses: ['response_id', 'session_token', 'question_index', 'response_text', 'audio_file_path'],
  interaction_events: ['event_id', 'session_token', 'event_type', 'payload_json', 'timestamp'],
};

function doPost(e) {
  try {
    const request = JSON.parse(e.postData && e.postData.contents ? e.postData.contents : '{}');
    if (!request.secret || request.secret !== API_SECRET) {
      return response_({ ok: false, error: 'Unauthorized storage request.' });
    }

    if (request.action === 'load_state') {
      return response_({ ok: true, state: loadState_() });
    }
    if (request.action === 'save_state') {
      saveState_(request.state || {});
      return response_({ ok: true });
    }
    if (request.action === 'upload_audio') {
      return response_({ ok: true, url: uploadAudio_(request) });
    }
    return response_({ ok: false, error: 'Unknown storage action.' });
  } catch (error) {
    return response_({ ok: false, error: String(error.message || error) });
  }
}

function response_(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function loadState_() {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  const state = { tables: {} };
  Object.keys(TABLES).forEach(function (name) {
    const sheet = spreadsheet.getSheetByName(name);
    if (!sheet || sheet.getLastRow() < 2) {
      state.tables[name] = [];
      return;
    }
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const rows = sheet.getRange(2, 1, sheet.getLastRow() - 1, headers.length).getValues();
    state.tables[name] = rows.map(function (row) {
      const record = {};
      headers.forEach(function (header, index) { record[header] = row[index]; });
      return record;
    });
  });
  return state;
}

function saveState_(state) {
  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const tables = state.tables || {};
    Object.keys(TABLES).forEach(function (name) {
      const headers = TABLES[name];
      let sheet = spreadsheet.getSheetByName(name);
      if (!sheet) sheet = spreadsheet.insertSheet(name);
      sheet.clearContents();
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      const rows = (tables[name] || []).map(function (record) {
        return headers.map(function (header) {
          const value = record[header];
          return value === null || value === undefined ? '' : value;
        });
      });
      if (rows.length) sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      sheet.setFrozenRows(1);
    });
  } finally {
    lock.releaseLock();
  }
}

function uploadAudio_(request) {
  const bytes = Utilities.base64Decode(request.audio_base64 || '');
  if (!bytes.length) throw new Error('No audio was received.');
  if (bytes.length > 5 * 1024 * 1024) throw new Error('Recording is over the 5 MB limit.');
  const stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd_HHmmss');
  const safeToken = String(request.session_token || 'participant').replace(/[^A-Za-z0-9_-]/g, '_');
  const blob = Utilities.newBlob(bytes, 'audio/wav', 'cardsort_' + safeToken + '_' + stamp + '.wav');
  const file = DriveApp.getFolderById(AUDIO_FOLDER_ID).createFile(blob);
  return file.getUrl();
}
