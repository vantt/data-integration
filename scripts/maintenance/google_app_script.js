/**
 * Marketing Spend Input Script
 * Attached to Google Sheet
 */

const SHEET_NAMES = {
  INPUT: 'Input',
  DATABASE: 'Database',
  METADATA: 'Metadata'
};

const UI_CONFIG = {
  START_ROW: 2, // Row where input starts
  // Cell mappings (Row, Col) for Input Sheet
  CELLS: {
    DATE: 'C3',
    SPEND_ITEM: 'C5',
    TARGET_CHANNEL: 'C7',
    CAMPAIGN_ID: 'C9',
    AMOUNT: 'C11',
    CLICKS: 'C13',
    IMPRESSIONS: 'C15'
  }
};

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Marketing Tools')
      .addItem('Save Record', 'saveRecord')
      .addItem('Clear Form', 'clearForm')
      .addToUi();
}

function saveRecord() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const inputSheet = ss.getSheetByName(SHEET_NAMES.INPUT);
  const dbSheet = ss.getSheetByName(SHEET_NAMES.DATABASE);
  const metaSheet = ss.getSheetByName(SHEET_NAMES.METADATA);

  if (!inputSheet || !dbSheet || !metaSheet) {
    SpreadsheetApp.getUi().alert('Error: Missing required sheets (Input, Database, Metadata).');
    return;
  }

  // 1. Get Values
  const data = {
    date: inputSheet.getRange(UI_CONFIG.CELLS.DATE).getValue(),
    spendItemName: inputSheet.getRange(UI_CONFIG.CELLS.SPEND_ITEM).getValue(),
    channelName: inputSheet.getRange(UI_CONFIG.CELLS.TARGET_CHANNEL).getValue(),
    campaignId: inputSheet.getRange(UI_CONFIG.CELLS.CAMPAIGN_ID).getValue(),
    amount: inputSheet.getRange(UI_CONFIG.CELLS.AMOUNT).getValue(),
    clicks: inputSheet.getRange(UI_CONFIG.CELLS.CLICKS).getValue(),
    impressions: inputSheet.getRange(UI_CONFIG.CELLS.IMPRESSIONS).getValue()
  };

  // 2. Validate
  if (!data.date || !data.spendItemName || !data.channelName || !data.amount) {
    SpreadsheetApp.getUi().alert('Please fill in all required fields (Date, Spend Item, Channel, Amount).');
    return;
  }

  // 3. Lookup Codes
  const spendCode = getLookupValue(metaSheet, data.spendItemName, 1, 2); // Col A -> B
  const channelRef = getLookupValue(metaSheet, data.channelName, 4, 5); // Col D -> E
  
  if (!spendCode) {
     SpreadsheetApp.getUi().alert('Error: Invalid Spend Item selected.');
     return;
  }
  if (!channelRef) {
     SpreadsheetApp.getUi().alert('Error: Invalid Channel selected.');
     return;
  }
  
  // Parse Channel Ref (SourceID|LocationID)
  const parts = channelRef.toString().split('|');
  const sourceId = parts[0];
  const locationId = parts[1] || '';

  // 4. Save to Database
  // Columns: Timestamp, Date, Spend Code, Target Channel Ref, Source ID, Location ID, Campaign ID, Amount, Clicks, Impressions
  dbSheet.appendRow([
    new Date(),
    data.date,
    spendCode,
    channelRef,
    sourceId,
    locationId,
    data.campaignId,
    data.amount,
    data.clicks || 0,
    data.impressions || 0
  ]);

  // 5. Clear Form (Optional: keep Date/Channel?)
  // inputSheet.getRange(UI_CONFIG.CELLS.CAMPAIGN_ID).clearContent();
  inputSheet.getRange(UI_CONFIG.CELLS.AMOUNT).clearContent();
  inputSheet.getRange(UI_CONFIG.CELLS.CLICKS).clearContent();
  inputSheet.getRange(UI_CONFIG.CELLS.IMPRESSIONS).clearContent();
  
  SpreadsheetApp.getUi().alert('Saved successfully!');
}

function clearForm() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAMES.INPUT);
  sheet.getRange(UI_CONFIG.CELLS.AMOUNT).clearContent();
  sheet.getRange(UI_CONFIG.CELLS.CLICKS).clearContent();
  sheet.getRange(UI_CONFIG.CELLS.IMPRESSIONS).clearContent();
  sheet.getRange(UI_CONFIG.CELLS.CAMPAIGN_ID).clearContent();
}

/**
 * Helper to find value in a sheet
 * searchCol: 1-based index of column to search
 * returnCol: 1-based index of column to return
 */
function getLookupValue(sheet, searchKey, searchCol, returnCol) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;
  
  const range = sheet.getRange(2, 1, lastRow - 1, Math.max(searchCol, returnCol));
  const values = range.getValues();
  
  for (let i = 0; i < values.length; i++) {
    if (values[i][searchCol - 1] === searchKey) {
      return values[i][returnCol - 1];
    }
  }
  return null;
}
