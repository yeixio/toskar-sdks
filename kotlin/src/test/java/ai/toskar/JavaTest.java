package ai.toskar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import ai.toskar.api.ChatRequest;
import java.io.IOException;
import mockwebserver3.MockResponse;
import mockwebserver3.MockWebServer;
import org.junit.jupiter.api.Test;

/** The SDK as Java uses it: constructors, overloads, streams, and errors. */
class JavaTest {
    @Test
    void chatsAndStreamsFromJava() throws IOException {
        try (MockWebServer core = new MockWebServer()) {
            core.start();
            core.enqueue(new MockResponse.Builder().setHeader("Content-Type", "text/event-stream")
                    .body("event: token\ndata: {\"content\":\"Hi\"}\n\nevent: done\ndata: {}\n\n").build());
            core.enqueue(new MockResponse.Builder().code(404)
                    .body("{\"error\":{\"code\":\"MODEL_NOT_FOUND\",\"message\":\"No such model\"}}").build());

            try (Toskar toskar = new Toskar(core.url("/").toString(), "secret")) {
                StringBuilder text = new StringBuilder();
                try (EventStream<ChatEvent> events = toskar.chatStream(new ChatRequest("Hi"))) {
                    for (ChatEvent event : events) {
                        if (event instanceof ChatEvent.Token) {
                            text.append(((ChatEvent.Token) event).getText());
                        }
                    }
                }
                assertEquals("Hi", text.toString());

                ToskarException e = assertThrows(ToskarException.class, () -> toskar.getApi().listModels());
                assertEquals(ErrorCodes.MODEL_NOT_FOUND, e.getCode());
                assertEquals(404, e.getStatus());
                assertEquals("1.60".substring(0, 1), Contract.CONTRACT_VERSION.substring(0, 1));
            }
        }
    }
}
