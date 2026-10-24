package toskar

import (
	"context"
	"crypto"
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/json"
	"errors"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

// Every SDK checks itself against Toskar Core's connection test vectors
// (spec/connection-vectors.json, docs/connecting.md).
func TestConnectionVectors(t *testing.T) {
	raw, err := os.ReadFile("../spec/connection-vectors.json")
	if err != nil {
		t.Fatal(err)
	}
	var v struct {
		Routes []struct {
			Secret  string `json:"secret"`
			RouteID string `json:"route_id"`
		} `json:"routes"`
		Pins []struct {
			CertDER     string `json:"cert_der_base64"`
			Fingerprint string `json:"fingerprint"`
			Short       string `json:"short"`
		} `json:"pins"`
		Records []struct {
			Name      string   `json:"name"`
			Blob      string   `json:"blob_base64"`
			Secret    string   `json:"secret"`
			Pin       string   `json:"pin"`
			Now       int64    `json:"now"`
			MaxAge    int64    `json:"max_age_seconds"`
			Addresses []string `json:"addresses"`
			At        int64    `json:"at"`
			Error     string   `json:"error"`
		} `json:"records"`
	}
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatal(err)
	}
	for _, r := range v.Routes {
		if got, err := RouteID(r.Secret); err != nil || got != r.RouteID {
			t.Errorf("route ID of %s: %s %v, want %s", r.Secret, got, err, r.RouteID)
		}
	}
	for _, p := range v.Pins {
		der, _ := base64.StdEncoding.DecodeString(p.CertDER)
		if PinOf(der) != p.Fingerprint || ShortPin(p.Fingerprint) != p.Short {
			t.Errorf("pin %s (%s), want %s (%s)", PinOf(der), ShortPin(PinOf(der)), p.Fingerprint, p.Short)
		}
	}
	for _, r := range v.Records {
		blob, _ := base64.StdEncoding.DecodeString(r.Blob)
		rec, err := OpenRecord(blob, r.Secret, r.Pin, time.Unix(r.Now, 0), time.Duration(r.MaxAge)*time.Second)
		if r.Error != "" {
			want := map[string]error{"sealed": ErrRecordSealed, "pin": ErrRecordPin, "stale": ErrRecordStale}[r.Error]
			if !errors.Is(err, want) {
				t.Errorf("%s: %v, want %s", r.Name, err, r.Error)
			}
			continue
		}
		if err != nil || rec.At.Unix() != r.At || strings.Join(rec.Addresses, ",") != strings.Join(r.Addresses, ",") {
			t.Errorf("%s: %+v %v", r.Name, rec, err)
		}
	}
}

// computer is a Toskar Core on TLS with a certificate of its own, as a
// computer's API listener is, counting the keys it's sent.
func computer(t *testing.T, pair func(w http.ResponseWriter, pin string)) (*httptest.Server, string, *atomic.Int32) {
	t.Helper()
	keys := &atomic.Int32{}
	var pin string
	srv := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "" {
			keys.Add(1)
		}
		switch r.URL.Path {
		case "/api/v1/health":
			_, _ = w.Write([]byte(`{"status":"ok"}`))
		case "/api/v1/devices/pair":
			pair(w, pin)
		default:
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`[]`))
		}
	}))
	// Each computer has a certificate of its own; httptest's is shared.
	srv.TLS = &tls.Config{Certificates: []tls.Certificate{ownCertificate(t)}}
	srv.StartTLS()
	t.Cleanup(srv.Close)
	pin = PinOf(srv.Certificate().Raw)
	return srv, pin, keys
}

func ownCertificate(t *testing.T) tls.Certificate {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Toskar test"},
		NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), IPAddresses: []net.IP{net.IPv4(127, 0, 0, 1)}}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, key.Public(), key)
	if err != nil {
		t.Fatal(err)
	}
	return tls.Certificate{Certificate: [][]byte{der}, PrivateKey: key}
}

func address(srv *httptest.Server) string { return strings.TrimPrefix(srv.URL, "https://") }

func TestPairPinsTheComputersCertificate(t *testing.T) {
	srv, pin, _ := computer(t, func(w http.ResponseWriter, pin string) {
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(map[string]any{"api_key": "tk_device", "tls_fingerprint": pin, "tls_short": ShortPin(pin), "key": map[string]any{"id": "k"},
			"route_secret": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8", "route_id": "2tmuvlcde47sagxxpvexynrgvmecwn6f", "relay": "relay.toskar.ai", "token": "rt"})
	})
	var shown string
	d, err := Pair(context.Background(), address(srv), "123456", "Test", func(short string) bool { shown = short; return true })
	if err != nil {
		t.Fatal(err)
	}
	if shown != ShortPin(pin) || d.Pin != pin || d.APIKey != "tk_device" || d.Route == nil || d.Route.Token != "rt" {
		t.Fatalf("paired %+v %+v, shown %s", d, d.Route, shown)
	}
	if _, err := Pair(context.Background(), address(srv), "123456", "Test", func(string) bool { return false }); !errors.Is(err, ErrNotConfirmed) {
		t.Fatalf("not confirmed: %v", err)
	}
}

func TestPairRefusesAFingerprintThatIsntTheCertificates(t *testing.T) {
	srv, _, _ := computer(t, func(w http.ResponseWriter, _ string) {
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(map[string]any{"api_key": "tk", "tls_fingerprint": "sha256:" + strings.Repeat("ab", 32), "tls_short": "ABAB-ABAB", "key": map[string]any{}})
	})
	if _, err := Pair(context.Background(), address(srv), "123456", "Test", nil); !errors.Is(err, ErrPinMismatch) {
		t.Fatalf("pair: %v", err)
	}
}

func TestAnotherCertificateNeverSeesTheKey(t *testing.T) {
	_, pin, _ := computer(t, nil)
	other, _, keys := computer(t, nil)
	c, err := New(WithDevice(Device{Address: address(other), APIKey: "tk_device", Pin: pin}), WithRetries(0))
	if err != nil {
		t.Fatal(err)
	}
	_, err = Data(c.ListModelsWithResponse(context.Background()))
	if !errors.Is(err, ErrPinMismatch) || keys.Load() != 0 {
		t.Fatalf("listed from another computer: %v, keys sent %d", err, keys.Load())
	}
}

func TestHomeFirst(t *testing.T) {
	srv, pin, keys := computer(t, nil)
	c, _ := New(WithDevice(Device{Address: address(srv), APIKey: "tk_device", Pin: pin}))
	if _, err := Data(c.ListModelsWithResponse(context.Background())); err != nil {
		t.Fatal(err)
	}
	if c.Path() != PathHome || keys.Load() == 0 {
		t.Fatalf("path %q, keys %d", c.Path(), keys.Load())
	}
}

// Away from home: home doesn't answer, so the address record says where
// the computer is, and its direct way in answers before the relay's.
func TestAwayThroughTheRecord(t *testing.T) {
	srv, pin, _ := computer(t, nil)
	secret := "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
	route, _ := RouteID(secret)
	blob := seal(t, srv, secret, []string{address(srv), route + ".relay.test:4443"})
	var tokens []string
	relay := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tokens = append(tokens, r.Header.Get("Authorization"))
		if r.URL.Path != "/v1/routes/"+route+"/record" {
			http.NotFound(w, r)
			return
		}
		_, _ = w.Write(blob)
	}))
	defer relay.Close()

	c, _ := New(WithDevice(Device{Address: unused(t), APIKey: "tk_device", Pin: pin,
		Route: &Route{Secret: secret, ID: route, Relay: address(relay), Token: "rt"}}))
	c.router.relayClient = relay.Client()
	if _, err := Data(c.ListModelsWithResponse(context.Background())); err != nil {
		t.Fatal(err)
	}
	if c.Path() != PathDirect || len(tokens) != 1 || tokens[0] != "Bearer rt" {
		t.Fatalf("path %q, relay asked with %v", c.Path(), tokens)
	}
}

func TestToskarsRelayIsntAskedWithoutAToken(t *testing.T) {
	_, pin, _ := computer(t, nil)
	asked := false
	c, _ := New(WithDevice(Device{Address: unused(t), APIKey: "tk", Pin: pin,
		Route: &Route{Secret: "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8", ID: "x", Relay: ToskarRelay}}), WithRetries(0))
	c.router.relayClient = &http.Client{Transport: roundTripFunc(func(*http.Request) (*http.Response, error) { asked = true; return nil, errors.New("no") })}
	if _, err := Data(c.ListModelsWithResponse(context.Background())); !errors.Is(err, ErrUnreachable) || asked {
		t.Fatalf("err %v, relay asked %v", err, asked)
	}
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

// unused is a local address nothing answers on, as home is when away.
func unused(t *testing.T) string {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	a := l.Addr().String()
	l.Close()
	return a
}

// seal writes an address record as the computer does (Toskar Core's
// internal/rendezvous): signed with its certificate's key, sealed with the
// record key.
func seal(t *testing.T, srv *httptest.Server, secret string, addresses []string) []byte {
	t.Helper()
	route, _ := RouteID(secret)
	payload, _ := json.Marshal(map[string]any{"v": 1, "route": route, "at": time.Now().Unix(), "addresses": addresses})
	sum := sha256.Sum256(payload)
	var alg string
	var sig []byte
	var err error
	switch key := srv.TLS.Certificates[0].PrivateKey.(type) {
	case *ecdsa.PrivateKey:
		alg = "ecdsa-sha256"
		sig, err = ecdsa.SignASN1(rand.Reader, key, sum[:])
	case *rsa.PrivateKey:
		alg = "rsa-pkcs1-sha256"
		sig, err = rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, sum[:])
	default:
		t.Fatalf("a %T key", key)
	}
	if err != nil {
		t.Fatal(err)
	}
	plain, _ := json.Marshal(map[string]any{"payload": payload, "cert": srv.Certificate().Raw, "alg": alg, "sig": sig})
	s, _ := decodeSecret(secret)
	rk, _ := recordKey(s)
	block, _ := aes.NewCipher(rk)
	gcm, _ := cipher.NewGCM(block)
	nonce := make([]byte, gcm.NonceSize())
	_, _ = rand.Read(nonce)
	return gcm.Seal(nonce, nonce, plain, []byte(route))
}
