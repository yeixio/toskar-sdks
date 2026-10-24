// Package discover finds computers running Toskar Core on the home network,
// as the Toskar apps do: they advertise _localai._tcp over mDNS, with where
// their API is in the TXT record (Toskar Core's docs/connecting.md).
//
//	computers, err := discover.Find(ctx, 3*time.Second)
//	device, err := toskar.Pair(ctx, computers[0].Address, code, "Kitchen tablet", confirm)
package discover

import (
	"context"
	"net"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/grandcat/zeroconf"
)

// ServiceType is what Toskar Core advertises.
const ServiceType = "_localai._tcp"

// Computer is a Toskar Core found on the network.
type Computer struct {
	Name   string
	NodeID string
	// Version is Toskar Core's version.
	Version string
	// Address is the API's host:port, to pair with: the first of Addresses
	// that answers.
	Address string
	// Addresses are every host:port the computer advertised. A computer can
	// advertise addresses this device can't reach, such as a container
	// network's.
	Addresses []string
	// OnNetwork is false when the API answers only on that computer: say to
	// turn on Connect a device there, rather than that it's unreachable.
	OnNetwork bool
}

// Find browses for timeout and returns the computers that answered, by
// name.
func Find(ctx context.Context, timeout time.Duration) ([]Computer, error) {
	resolver, err := zeroconf.NewResolver(nil)
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	entries := make(chan *zeroconf.ServiceEntry)
	found := map[string]Computer{}
	done := make(chan struct{})
	go func() {
		defer close(done)
		for e := range entries {
			if c, ok := computerOf(e); ok {
				found[c.NodeID+c.Address] = c
			}
		}
	}()
	if err := resolver.Browse(ctx, ServiceType, "local.", entries); err != nil {
		return nil, err
	}
	<-ctx.Done()
	<-done
	out := make([]Computer, 0, len(found))
	for _, c := range found {
		out = append(out, c)
	}
	for i := range out {
		out[i].Address = reachable(out[i].Addresses)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out, nil
}

// reachable is the first of addresses that takes a TCP connection, tried
// together; the first, when none does.
func reachable(addresses []string) string {
	if len(addresses) < 2 {
		return addresses[0]
	}
	answered := make(chan string, len(addresses))
	for _, a := range addresses {
		go func() {
			if c, err := net.DialTimeout("tcp", a, 700*time.Millisecond); err == nil {
				c.Close()
				answered <- a
				return
			}
			answered <- ""
		}()
	}
	for range addresses {
		if a := <-answered; a != "" {
			return a
		}
	}
	return addresses[0]
}

func computerOf(e *zeroconf.ServiceEntry) (Computer, bool) {
	txt := map[string]string{}
	for _, line := range e.Text {
		if k, v, ok := strings.Cut(line, "="); ok {
			txt[k] = v
		}
	}
	// The service's own port is for computers pairing with each other; the
	// API's is in api_port.
	port, err := strconv.Atoi(txt["api_port"])
	if err != nil || port <= 0 {
		return Computer{}, false
	}
	var addresses []string
	for _, ip := range e.AddrIPv4 {
		addresses = append(addresses, net.JoinHostPort(ip.String(), strconv.Itoa(port)))
	}
	for _, ip := range e.AddrIPv6 {
		addresses = append(addresses, net.JoinHostPort(ip.String(), strconv.Itoa(port)))
	}
	if len(addresses) == 0 {
		return Computer{}, false
	}
	name := txt["name"]
	if name == "" {
		name = e.Instance
	}
	return Computer{
		Name:      name,
		NodeID:    txt["node_id"],
		Version:   txt["version"],
		Address:   addresses[0],
		Addresses: addresses,
		OnNetwork: txt["api_lan"] != "false",
	}, true
}
