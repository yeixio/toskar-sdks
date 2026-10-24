package toskar

import (
	"encoding/json"
	"fmt"
	"reflect"
)

// APIError is an error from Toskar Core: {"error": {"code", "message",
// "details"}}. Code is stable, such as ErrorCodeNoModelInstalled; Message
// is English text for logs; Details has the values the message needs.
//
//	var e *toskar.APIError
//	if errors.As(err, &e) && e.Code == toskar.ErrorCodeNoModelInstalled { … }
type APIError struct {
	Status  int
	Code    string
	Message string
	Details map[string]any
}

func (e *APIError) Error() string { return fmt.Sprintf("toskar: %s (%d %s)", e.Message, e.Status, e.Code) }

// errorFrom is the error a response body describes, or a generic one for a
// body that isn't Toskar's.
func errorFrom(status int, body []byte) *APIError {
	var b struct {
		Error *struct {
			Code    string         `json:"code"`
			Message string         `json:"message"`
			Details map[string]any `json:"details"`
		} `json:"error"`
	}
	if json.Unmarshal(body, &b) == nil && b.Error != nil && b.Error.Code != "" {
		msg := b.Error.Message
		if msg == "" {
			msg = b.Error.Code
		}
		return &APIError{Status: status, Code: b.Error.Code, Message: msg, Details: b.Error.Details}
	}
	return &APIError{Status: status, Code: fmt.Sprintf("HTTP_%d", status), Message: fmt.Sprintf("Toskar answered %d", status)}
}

// Data returns the 200 answer of a generated call, or its error: the
// call's own, or the *APIError Toskar answered with.
//
//	models, err := toskar.Data(c.ListModelsWithResponse(ctx))
func Data[T any, R interface {
	StatusCode() int
	GetJSON200() *T
}](r R, err error) (T, error) {
	var zero T
	if err != nil {
		return zero, err
	}
	if status := r.StatusCode(); status >= 300 {
		return zero, errorFrom(status, bodyOf(r))
	}
	if data := r.GetJSON200(); data != nil {
		return *data, nil
	}
	return zero, &APIError{Status: r.StatusCode(), Code: "NO_CONTENT", Message: "Toskar's answer had no JSON"}
}

// Check returns nil for a successful generated call, or its error. It suits
// calls that answer nothing, such as deletes.
func Check(r interface{ StatusCode() int }, err error) error {
	if err != nil {
		return err
	}
	if status := r.StatusCode(); status >= 300 {
		return errorFrom(status, bodyOf(r))
	}
	return nil
}

// bodyOf is a generated response's Body.
func bodyOf(r any) []byte {
	v := reflect.Indirect(reflect.ValueOf(r))
	if v.Kind() == reflect.Struct {
		if f := v.FieldByName("Body"); f.IsValid() {
			if b, ok := f.Interface().([]byte); ok {
				return b
			}
		}
	}
	return nil
}

