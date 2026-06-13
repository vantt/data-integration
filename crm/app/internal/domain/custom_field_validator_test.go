// Package domain — unit tests for custom-field validation (pure; no DB).
package domain

import (
	"strings"
	"testing"
)

// makeDef is a helper to construct a CustomFieldDef for tests.
func makeDef(key, dataType string, required bool, options ...string) CustomFieldDef {
	return CustomFieldDef{
		FieldID:    "test-" + key,
		EntityType: "party",
		FieldKey:   key,
		Label:      key,
		DataType:   dataType,
		Options:    options,
		IsRequired: required,
		IsActive:   true,
	}
}

// ─── ValidateCustomField ──────────────────────────────────────────────────────

func TestValidateCustomField_Text_Valid(t *testing.T) {
	def := makeDef("notes", "text", false)
	if err := ValidateCustomField(def, "any string"); err != nil {
		t.Errorf("expected nil, got %v", err)
	}
}

func TestValidateCustomField_Text_EmptyOptional(t *testing.T) {
	def := makeDef("notes", "text", false)
	if err := ValidateCustomField(def, ""); err != nil {
		t.Errorf("expected nil for empty optional text, got %v", err)
	}
}

func TestValidateCustomField_Required_Missing(t *testing.T) {
	def := makeDef("name", "text", true)
	err := ValidateCustomField(def, "")
	if err == nil {
		t.Fatal("expected error for missing required field")
	}
	if !strings.Contains(err.Error(), "required") {
		t.Errorf("expected 'required' in error, got: %v", err)
	}
}

func TestValidateCustomField_Number_Valid(t *testing.T) {
	def := makeDef("age", "number", false)
	for _, v := range []string{"0", "42", "3.14", "-10", "1e5"} {
		if err := ValidateCustomField(def, v); err != nil {
			t.Errorf("number %q: expected nil, got %v", v, err)
		}
	}
}

func TestValidateCustomField_Number_Invalid(t *testing.T) {
	def := makeDef("age", "number", false)
	err := ValidateCustomField(def, "not-a-number")
	if err == nil {
		t.Fatal("expected error for invalid number")
	}
}

func TestValidateCustomField_Date_Valid(t *testing.T) {
	def := makeDef("birthday", "date", false)
	if err := ValidateCustomField(def, "1990-05-20"); err != nil {
		t.Errorf("expected nil for valid date, got %v", err)
	}
}

func TestValidateCustomField_Date_Invalid(t *testing.T) {
	def := makeDef("birthday", "date", false)
	for _, bad := range []string{"20-05-1990", "1990/05/20", "not-a-date", "1990-13-01"} {
		err := ValidateCustomField(def, bad)
		if err == nil {
			t.Errorf("date %q: expected error, got nil", bad)
		}
	}
}

func TestValidateCustomField_Bool_Valid(t *testing.T) {
	def := makeDef("consent", "bool", false)
	for _, v := range []string{"true", "false", "True", "FALSE"} {
		if err := ValidateCustomField(def, v); err != nil {
			t.Errorf("bool %q: expected nil, got %v", v, err)
		}
	}
}

func TestValidateCustomField_Bool_Invalid(t *testing.T) {
	def := makeDef("consent", "bool", false)
	err := ValidateCustomField(def, "yes")
	if err == nil {
		t.Fatal("expected error for invalid bool value 'yes'")
	}
}

func TestValidateCustomField_Select_Valid(t *testing.T) {
	def := makeDef("skin", "select", false, "dầu", "khô", "hỗn hợp")
	if err := ValidateCustomField(def, "dầu"); err != nil {
		t.Errorf("expected nil for valid select value, got %v", err)
	}
}

func TestValidateCustomField_Select_Invalid(t *testing.T) {
	def := makeDef("skin", "select", false, "dầu", "khô")
	err := ValidateCustomField(def, "nhạy cảm")
	if err == nil {
		t.Fatal("expected error for value not in select options")
	}
	if !strings.Contains(err.Error(), "not in allowed options") {
		t.Errorf("expected 'not in allowed options', got: %v", err)
	}
}

func TestValidateCustomField_Multiselect_Valid(t *testing.T) {
	def := makeDef("channels", "multiselect", false, "phone", "zalo", "email")
	if err := ValidateCustomField(def, "phone,email"); err != nil {
		t.Errorf("expected nil for valid multiselect, got %v", err)
	}
}

func TestValidateCustomField_Multiselect_OneInvalid(t *testing.T) {
	def := makeDef("channels", "multiselect", false, "phone", "zalo", "email")
	err := ValidateCustomField(def, "phone,sms")
	if err == nil {
		t.Fatal("expected error when one multiselect item is invalid")
	}
	if !strings.Contains(err.Error(), "sms") {
		t.Errorf("expected 'sms' in error, got: %v", err)
	}
}

// ─── ValidateCustomMap ────────────────────────────────────────────────────────

func TestValidateCustomMap_AllValid(t *testing.T) {
	defs := []CustomFieldDef{
		makeDef("skin_type", "select", false, "dầu", "khô"),
		makeDef("age", "number", false),
	}
	m := map[string]string{"skin_type": "dầu", "age": "30"}
	errs := ValidateCustomMap(defs, m)
	if len(errs) != 0 {
		t.Errorf("expected no errors, got: %v", errs)
	}
}

func TestValidateCustomMap_RequiredMissing(t *testing.T) {
	defs := []CustomFieldDef{
		makeDef("skin_type", "select", true, "dầu", "khô"),
	}
	m := map[string]string{} // skin_type missing
	errs := ValidateCustomMap(defs, m)
	if len(errs) == 0 {
		t.Fatal("expected error for missing required field")
	}
	if errs[0].FieldKey != "skin_type" {
		t.Errorf("expected error on skin_type, got %q", errs[0].FieldKey)
	}
}

func TestValidateCustomMap_UnknownKeyAllowed(t *testing.T) {
	defs := []CustomFieldDef{makeDef("age", "number", false)}
	// "unknown_key" is not in defs — must pass through silently.
	m := map[string]string{"age": "25", "unknown_key": "whatever"}
	errs := ValidateCustomMap(defs, m)
	if len(errs) != 0 {
		t.Errorf("unknown keys should be allowed; got errors: %v", errs)
	}
}

func TestValidateCustomMap_MultipleErrors(t *testing.T) {
	defs := []CustomFieldDef{
		makeDef("skin_type", "select", true, "dầu", "khô"),
		makeDef("age", "number", false),
	}
	// skin_type invalid value AND age not a number — expect 2 errors.
	m := map[string]string{"skin_type": "bad-value", "age": "not-a-number"}
	errs := ValidateCustomMap(defs, m)
	if len(errs) != 2 {
		t.Errorf("expected 2 errors, got %d: %v", len(errs), errs)
	}
}

func TestValidateCustomMap_InactiveDefIgnored(t *testing.T) {
	// An inactive def with is_required=true must NOT fire a required error.
	def := makeDef("old_field", "text", true)
	def.IsActive = false
	defs := []CustomFieldDef{def}
	m := map[string]string{} // old_field absent — but inactive, so no error
	errs := ValidateCustomMap(defs, m)
	if len(errs) != 0 {
		t.Errorf("inactive def should be skipped; got errors: %v", errs)
	}
}
