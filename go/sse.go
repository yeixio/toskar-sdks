package toskar

import (
	"bufio"
	"io"
	"iter"
	"strings"
)

// ServerSentEvent is one server-sent event: its name ("message" without
// one) and its data.
type ServerSentEvent struct {
	Event string
	Data  string
}

// ReadEvents yields the server-sent events in r as they arrive. Comments,
// such as ": ping", are skipped.
func ReadEvents(r io.Reader) iter.Seq2[ServerSentEvent, error] {
	return func(yield func(ServerSentEvent, error) bool) {
		scan := bufio.NewScanner(r)
		scan.Buffer(make([]byte, 64<<10), 8<<20)
		event, data := "message", []string(nil)
		flush := func() bool {
			if data == nil {
				event = "message"
				return true
			}
			e := ServerSentEvent{Event: event, Data: strings.Join(data, "\n")}
			event, data = "message", nil
			return yield(e, nil)
		}
		for scan.Scan() {
			line := strings.TrimSuffix(scan.Text(), "\r")
			if line == "" {
				if !flush() {
					return
				}
				continue
			}
			if strings.HasPrefix(line, ":") {
				continue
			}
			field, value, _ := strings.Cut(line, ":")
			value = strings.TrimPrefix(value, " ")
			switch field {
			case "event":
				event = value
			case "data":
				data = append(data, value)
			}
		}
		if err := scan.Err(); err != nil {
			yield(ServerSentEvent{}, err)
			return
		}
		flush()
	}
}
