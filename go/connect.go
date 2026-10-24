package toskar

import (
	"bytes"
	"context"
	"crypto"
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/hkdf"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/base32"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/yeixio/toskar-sdks/go/api"
)

// Connecting as a paired device, as the Toskar apps do (Toskar Core's
// docs/connecting.md): pairing with the code Connect a device shows, the
// computer's certificate pinned on every connection, and reaching it at
// home or, with access from anywhere, directly or through its relay.

// Device is what a paired device keeps, to connect again. Save it as a
// password is saved: APIKey and the route's Secret and Token are secrets.
type Device struct {
	// Address is the computer's host:port at home.
	Address string `json:"address"`
	APIKey  string `json:"api_key"`
	// Pin is "sha256:<hex>" of the computer's certificate. It only ever
	// comes from pairing.
	Pin   string `json:"pin"`
	Route *Route `json:"route,omitempty"`
}

// Route is how to find the computer away from home, when it has access
// from anywhere.
type Route struct {
	// Secret is the route secret, base64url without padding.
	Secret string `json:"secret"`
	ID     string `json:"id"`
	// Relay is the relay the computer uses, such as relay.toskar.ai.
	Relay string `json:"relay"`
	// Token lets the device look the computer up on Toskar's relay.
	Token string `json:"token,omitempty"`
}

// ToskarRelay is Toskar's own relay. It's asked only with a route token.
const ToskarRelay = "relay.toskar.ai"

// Path is how the client reaches its computer.
type Path string

const (
	PathHome   Path = "home"
	PathDirect Path = "direct"
	PathRelay  Path = "relay"
)

// Errors from pairing and connecting.
var (
	// ErrPinMismatch is a computer whose certificate isn't the pinned one:
	// stop, and pair again to trust a new certificate.
	ErrPinMismatch = errors.New("toskar: the computer's certificate isn't the one paired with")
	// ErrNotConfirmed is pairing the person stopped at the short pin.
	ErrNotConfirmed = errors.New("toskar: the short pin wasn't confirmed")
	// ErrUnreachable is no way in answering, at home or away.
	ErrUnreachable = errors.New("toskar: the computer can't be reached")
	// ErrNoRecord is no address record to find the computer away from home:
	// it may be off or asleep, or have no access from anywhere.
	ErrNoRecord = errors.New("toskar: no address record for the computer")

	ErrRecordSealed = errors.New("toskar: the record doesn't open with this route secret")
	ErrRecordPin    = errors.New("toskar: the record isn't from the pinned computer")
	ErrRecordStale  = errors.New("toskar: the record is too old")
)

// PinOf is the pin of a certificate: "sha256:<hex>" of its DER.
func PinOf(der []byte) string {
	sum := sha256.Sum256(der)
	return "sha256:" + hex.EncodeToString(sum[:])
}

// ShortPin is how a pin is shown for the person to compare: its first 8
// hex digits, as ABCD-1234.
func ShortPin(pin string) string {
	h := strings.ToUpper(strings.TrimPrefix(pin, "sha256:"))
	if len(h) < 8 {
		return h
	}
	return h[:4] + "-" + h[4:8]
}

// pinnedTLS trusts exactly the certificate with pin, checked before any
// request is sent; names, dates, and signers aren't checked. Seen, when
// set, gets the certificate's pin, for pairing.
func pinnedTLS(pin string, seen func(string)) *tls.Config {
	return &tls.Config{
		InsecureSkipVerify: true, // the pin is the trust, checked below
		VerifyConnection: func(cs tls.ConnectionState) error {
			if len(cs.PeerCertificates) == 0 {
				return ErrPinMismatch
			}
			got := PinOf(cs.PeerCertificates[0].Raw)
			if seen != nil {
				seen(got)
				return nil
			}
			if !strings.EqualFold(got, pin) {
				return ErrPinMismatch
			}
			return nil
		},
	}
}

func pinnedTransport(pin string, timeout time.Duration) *http.Transport {
	t := http.DefaultTransport.(*http.Transport).Clone()
	t.TLSClientConfig = pinnedTLS(pin, nil)
	t.ResponseHeaderTimeout = timeout
	return t
}

// ConfirmPin shows the person the short pin and says whether it's the one
// the computer shows. Nil skips the check, as a script with no one to ask
// does.
type ConfirmPin func(shortPin string) bool

// Pair pairs with the computer at address (host:port, as found or typed)
// using the code Connect a device shows on it. The device must be on the
// computer's local network.
func Pair(ctx context.Context, address, code, deviceName string, confirm ConfirmPin) (*Device, error) {
	// The certificate the computer shows, for the person to check.
	var seen string
	dialer := &tls.Dialer{Config: pinnedTLS("", func(p string) { seen = p })}
	conn, err := dialer.DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, err
	}
	conn.Close()
	if confirm != nil && !confirm(ShortPin(seen)) {
		return nil, ErrNotConfirmed
	}

	// Then the code, to that certificate alone.
	hc := &http.Client{Transport: pinnedTransport(seen, 30*time.Second)}
	body, _ := json.Marshal(map[string]string{"code": code, "device_name": deviceName})
	r, err := http.NewRequestWithContext(ctx, http.MethodPost, "https://"+address+"/api/v1/devices/pair", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Toskar-Client-Contract", ContractVersion)
	resp, err := hc.Do(r)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 300 {
		return nil, errorFrom(resp.StatusCode, raw)
	}
	var paired api.PairedDevice
	if err := json.Unmarshal(raw, &paired); err != nil {
		return nil, err
	}
	if !strings.EqualFold(paired.TlsFingerprint, seen) {
		return nil, ErrPinMismatch
	}
	d := &Device{Address: address, APIKey: paired.ApiKey, Pin: seen}
	if paired.RouteSecret != nil && *paired.RouteSecret != "" {
		d.Route = &Route{Secret: *paired.RouteSecret, ID: deref(paired.RouteId), Relay: deref(paired.Relay), Token: deref(paired.Token)}
	}
	return d, nil
}

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// WithDevice connects as a paired device: every connection pinned to its
// computer's certificate, at home when it answers, and otherwise directly
// or through its relay, from its address record.
func WithDevice(d Device) Option {
	return func(o *options) {
		o.device = &d
		o.baseURL = "https://" + d.Address
		o.apiKey = d.APIKey
	}
}

// Route IDs and record keys, from the route secret.

var lowerBase32 = base32.NewEncoding("abcdefghijklmnopqrstuvwxyz234567").WithPadding(base32.NoPadding)

func decodeSecret(secret string) ([]byte, error) {
	b, err := base64.RawURLEncoding.DecodeString(secret)
	if err != nil || len(b) != 32 {
		return nil, errors.New("toskar: a route secret is 32 bytes, base64url")
	}
	return b, nil
}

// RouteID is the route ID a route secret names.
func RouteID(secret string) (string, error) {
	s, err := decodeSecret(secret)
	if err != nil {
		return "", err
	}
	b, err := hkdf.Key(sha256.New, s, nil, "toskar route id", 20)
	return lowerBase32.EncodeToString(b), err
}

func recordKey(secret []byte) ([]byte, error) {
	return hkdf.Key(sha256.New, secret, nil, "toskar route key", 32)
}

// Record is what an address record says: the computer's ways in, and when
// it wrote them.
type Record struct {
	Addresses []string
	At        time.Time
}

// OpenRecord opens an address record as docs/connecting.md says: sealed
// with the route secret, from the certificate with pin, for this route, and
// no older than maxAge.
func OpenRecord(blob []byte, secret, pin string, now time.Time, maxAge time.Duration) (*Record, error) {
	s, err := decodeSecret(secret)
	if err != nil {
		return nil, err
	}
	route, _ := RouteID(secret)
	key, err := recordKey(s)
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(blob) < gcm.NonceSize() {
		return nil, ErrRecordSealed
	}
	plain, err := gcm.Open(nil, blob[:gcm.NonceSize()], blob[gcm.NonceSize():], []byte(route))
	if err != nil {
		return nil, ErrRecordSealed
	}
	var rec struct {
		Payload []byte `json:"payload"`
		Cert    []byte `json:"cert"`
		Alg     string `json:"alg"`
		Sig     []byte `json:"sig"`
	}
	if err := json.Unmarshal(plain, &rec); err != nil {
		return nil, ErrRecordSealed
	}
	if !strings.EqualFold(PinOf(rec.Cert), pin) {
		return nil, ErrRecordPin
	}
	cert, err := x509.ParseCertificate(rec.Cert)
	if err != nil || !verifySignature(cert.PublicKey, rec.Alg, rec.Payload, rec.Sig) {
		return nil, ErrRecordPin
	}
	var body struct {
		V         int      `json:"v"`
		Route     string   `json:"route"`
		At        int64    `json:"at"`
		Addresses []string `json:"addresses"`
	}
	if err := json.Unmarshal(rec.Payload, &body); err != nil || body.V != 1 || body.Route != route {
		return nil, ErrRecordPin
	}
	at := time.Unix(body.At, 0)
	if now.Sub(at) > maxAge || at.Sub(now) > 5*time.Minute {
		return nil, ErrRecordStale
	}
	return &Record{Addresses: body.Addresses, At: at}, nil
}

func verifySignature(pub any, alg string, payload, sig []byte) bool {
	sum := sha256.Sum256(payload)
	switch k := pub.(type) {
	case *ecdsa.PublicKey:
		return alg == "ecdsa-sha256" && ecdsa.VerifyASN1(k, sum[:], sig)
	case *rsa.PublicKey:
		return alg == "rsa-pkcs1-sha256" && rsa.VerifyPKCS1v15(k, crypto.SHA256, sum[:], sig) == nil
	case ed25519.PublicKey:
		return alg == "ed25519" && ed25519.Verify(k, payload, sig)
	}
	return false
}

// Choosing the way in.

const (
	homeTimeout  = 2500 * time.Millisecond
	tryTimeout   = 6 * time.Second
	relayDelay   = time.Second
	recordMaxAge = time.Hour
)

// router sends each request to the way in in use, choosing it again when
// it stops answering.
type router struct {
	device *Device
	next   http.RoundTripper // pinned
	// relayClient fetches address records from the relay, over its own
	// certificate, checked as any website's is.
	relayClient *http.Client

	mu   sync.Mutex
	way  string // host:port in use, or "" to choose again
	path Path
	now  func() time.Time
}

func (r *router) RoundTrip(req *http.Request) (*http.Response, error) {
	way, err := r.current(req.Context())
	if err != nil {
		return nil, err
	}
	out := req.Clone(req.Context())
	out.URL.Host = way
	out.Host = way
	resp, err := r.next.RoundTrip(out)
	if err != nil && !errors.Is(err, ErrPinMismatch) {
		// Choose again for the next request; a safe one is retried.
		r.mu.Lock()
		if r.way == way {
			r.way, r.path = "", ""
		}
		r.mu.Unlock()
	}
	return resp, err
}

func (r *router) current(ctx context.Context) (string, error) {
	r.mu.Lock()
	way := r.way
	r.mu.Unlock()
	if way != "" {
		return way, nil
	}
	path, way, err := r.choose(ctx)
	if err != nil {
		return "", err
	}
	r.mu.Lock()
	r.way, r.path = way, path
	r.mu.Unlock()
	return way, nil
}

// answers is whether the computer answers /api/v1/health at address,
// pinned, within timeout; err is ErrPinMismatch when something answered
// with another certificate.
func (r *router) answers(ctx context.Context, address string, timeout time.Duration) (bool, error) {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://"+address+"/api/v1/health", nil)
	if err != nil {
		return false, err
	}
	resp, err := r.next.RoundTrip(req)
	if err != nil {
		if errors.Is(err, ErrPinMismatch) {
			return false, ErrPinMismatch
		}
		return false, nil
	}
	defer resp.Body.Close()
	var h struct {
		Status string `json:"status"`
	}
	return resp.StatusCode == http.StatusOK && json.NewDecoder(resp.Body).Decode(&h) == nil && h.Status == "ok", nil
}

// choose finds a way in: home, then the address record's ways, the direct
// ones at once and the relay's a second later.
func (r *router) choose(ctx context.Context) (Path, string, error) {
	ok, err := r.answers(ctx, r.device.Address, homeTimeout)
	if ok {
		return PathHome, r.device.Address, nil
	}
	if err != nil {
		// Home answered with another certificate: the computer's changed,
		// or it isn't the computer. Say so; pairing again is the way on.
		return "", "", err
	}
	route := r.device.Route
	if route == nil || route.Secret == "" {
		return "", "", ErrUnreachable
	}
	relay := strings.ToLower(hostOnly(route.Relay))
	// Toskar's relay answers only for a subscription; without one, it
	// isn't asked, so nothing about this device reaches it.
	if relay == ToskarRelay && route.Token == "" {
		return "", "", ErrUnreachable
	}
	record, err := r.record(ctx, route)
	if err != nil {
		return "", "", err
	}
	type found struct {
		path Path
		way  string
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	results := make(chan *found, len(record.Addresses))
	for _, address := range record.Addresses {
		path := PathDirect
		if strings.HasSuffix(strings.ToLower(hostOnly(address)), "."+relay) {
			path = PathRelay
		}
		go func() {
			if path == PathRelay {
				select {
				case <-time.After(relayDelay):
				case <-ctx.Done():
					results <- nil
					return
				}
			}
			// Another certificate at a way in is someone else's device there:
			// that way just doesn't count.
			if ok, _ := r.answers(ctx, address, tryTimeout); ok {
				results <- &found{path, address}
				return
			}
			results <- nil
		}()
	}
	for range record.Addresses {
		if f := <-results; f != nil {
			return f.path, f.way, nil
		}
	}
	return "", "", ErrUnreachable
}

func (r *router) record(ctx context.Context, route *Route) (*Record, error) {
	ctx, cancel := context.WithTimeout(ctx, tryTimeout)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://"+route.Relay+"/v1/routes/"+route.ID+"/record", nil)
	if err != nil {
		return nil, err
	}
	if route.Token != "" {
		req.Header.Set("Authorization", "Bearer "+route.Token)
	}
	resp, err := r.relayClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrNoRecord, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, ErrNoRecord
	}
	blob, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrNoRecord, err)
	}
	return OpenRecord(blob, route.Secret, r.device.Pin, r.now(), recordMaxAge)
}

func hostOnly(address string) string {
	if host, _, err := net.SplitHostPort(address); err == nil {
		return host
	}
	return address
}

// Path is how the client reaches its paired computer now, or "" before
// its first request, or for a client that isn't a paired device.
func (c *Client) Path() Path {
	if c.router == nil {
		return ""
	}
	c.router.mu.Lock()
	defer c.router.mu.Unlock()
	return c.router.path
}

// Reconnect chooses the way in again, as after the network changed, and
// says which it found.
func (c *Client) Reconnect(ctx context.Context) (Path, error) {
	if c.router == nil {
		return "", nil
	}
	c.router.mu.Lock()
	c.router.way, c.router.path = "", ""
	c.router.mu.Unlock()
	if _, err := c.router.current(ctx); err != nil {
		return "", err
	}
	return c.Path(), nil
}
