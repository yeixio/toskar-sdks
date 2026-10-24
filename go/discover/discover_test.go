package discover

import (
	"net"
	"testing"

	"github.com/grandcat/zeroconf"
)

func TestReadsWhereTheAPIIs(t *testing.T) {
	e := zeroconf.NewServiceEntry("studio", ServiceType, "local.")
	e.Port = 7330 // the service's own, for computers pairing with each other
	e.AddrIPv4 = []net.IP{net.ParseIP("192.168.1.20")}
	e.Text = []string{"node_id=n1", "name=Studio", "version=1.11.0", "pairing=false", "api_port=7331", "api_lan=true"}
	c, ok := computerOf(e)
	if !ok || c.Address != "192.168.1.20:7331" || len(c.Addresses) != 1 || c.Name != "Studio" || !c.OnNetwork || c.Version != "1.11.0" {
		t.Fatalf("%+v %v", c, ok)
	}
	e.Text = []string{"node_id=n2", "api_port=7331", "api_lan=false"}
	e.AddrIPv4 = nil
	e.AddrIPv6 = []net.IP{net.ParseIP("fe80::1")}
	if c, ok := computerOf(e); !ok || c.Address != "[fe80::1]:7331" || c.OnNetwork || c.Name != "studio" {
		t.Fatalf("%+v", c)
	}
	e.Text = []string{"node_id=n3"}
	if _, ok := computerOf(e); ok {
		t.Fatal("a computer without api_port was found")
	}
}

func TestPrefersAnAddressThatAnswers(t *testing.T) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	go func() {
		for {
			c, err := l.Accept()
			if err != nil {
				return
			}
			c.Close()
		}
	}()
	// 10.255.255.1 stands for an address that doesn't route from here, such as a container network's.
	if got := reachable([]string{"10.255.255.1:7331", l.Addr().String()}); got != l.Addr().String() {
		t.Fatalf("chose %s", got)
	}
}
