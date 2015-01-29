# -*- coding: utf-8 -*-
# Copyright 2015 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple
from tests import unittest
from twisted.internet import defer

from mock import Mock, NonCallableMock
from tests.utils import (
    MockHttpResource, MockClock, DeferredMockCallable, SQLiteMemoryDbPool,
    MockKey
)

from synapse.server import HomeServer


user_localpart = "test_user"
MockEvent = namedtuple("MockEvent", "sender type room_id")

class FilteringTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        db_pool = SQLiteMemoryDbPool()
        yield db_pool.prepare()

        self.mock_config = NonCallableMock()
        self.mock_config.signing_key = [MockKey()]

        self.mock_federation_resource = MockHttpResource()

        self.mock_http_client = Mock(spec=[])
        self.mock_http_client.put_json = DeferredMockCallable()

        hs = HomeServer("test",
            db_pool=db_pool,
            handlers=None,
            http_client=self.mock_http_client,
            config=self.mock_config,
            keyring=Mock(),
        )

        self.filtering = hs.get_filtering()

        self.datastore = hs.get_datastore()

    def test_definition_types_works_with_literals(self):
        definition = {
            "types": ["m.room.message", "org.matrix.foo.bar"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!foo:bar"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_types_works_with_wildcards(self):
        definition = {
            "types": ["m.*", "org.matrix.foo.bar"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!foo:bar"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_types_works_with_unknowns(self):
        definition = {
            "types": ["m.room.message", "org.matrix.foo.bar"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="now.for.something.completely.different",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_types_works_with_literals(self):
        definition = {
            "not_types": ["m.room.message", "org.matrix.foo.bar"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_types_works_with_wildcards(self):
        definition = {
            "not_types": ["m.room.message", "org.matrix.*"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="org.matrix.custom.event",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_types_works_with_unknowns(self):
        definition = {
            "not_types": ["m.*", "org.*"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="com.nom.nom.nom",
            room_id="!foo:bar"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_types_takes_priority_over_types(self):
        definition = {
            "not_types": ["m.*", "org.*"],
            "types": ["m.room.message", "m.room.topic"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.topic",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_senders_works_with_literals(self):
        definition = {
            "senders": ["@flibble:wibble"]
        }
        event = MockEvent(
            sender="@flibble:wibble",
            type="com.nom.nom.nom",
            room_id="!foo:bar"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_senders_works_with_unknowns(self):
        definition = {
            "senders": ["@flibble:wibble"]
        }
        event = MockEvent(
            sender="@challenger:appears",
            type="com.nom.nom.nom",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_senders_works_with_literals(self):
        definition = {
            "not_senders": ["@flibble:wibble"]
        }
        event = MockEvent(
            sender="@flibble:wibble",
            type="com.nom.nom.nom",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_senders_works_with_unknowns(self):
        definition = {
            "not_senders": ["@flibble:wibble"]
        }
        event = MockEvent(
            sender="@challenger:appears",
            type="com.nom.nom.nom",
            room_id="!foo:bar"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_senders_takes_priority_over_senders(self):
        definition = {
            "not_senders": ["@misspiggy:muppets"],
            "senders": ["@kermit:muppets", "@misspiggy:muppets"]
        }
        event = MockEvent(
            sender="@misspiggy:muppets",
            type="m.room.topic",
            room_id="!foo:bar"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_rooms_works_with_literals(self):
        definition = {
            "rooms": ["!secretbase:unknown"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!secretbase:unknown"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_rooms_works_with_unknowns(self):
        definition = {
            "rooms": ["!secretbase:unknown"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!anothersecretbase:unknown"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_rooms_works_with_literals(self):
        definition = {
            "not_rooms": ["!anothersecretbase:unknown"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!anothersecretbase:unknown"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_rooms_works_with_unknowns(self):
        definition = {
            "not_rooms": ["!secretbase:unknown"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!anothersecretbase:unknown"
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_not_rooms_takes_priority_over_rooms(self):
        definition = {
            "not_rooms": ["!secretbase:unknown"],
            "rooms": ["!secretbase:unknown"]
        }
        event = MockEvent(
            sender="@foo:bar",
            type="m.room.message",
            room_id="!secretbase:unknown"
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_combined_event(self):
        definition = {
            "not_senders": ["@misspiggy:muppets"],
            "senders": ["@kermit:muppets"],
            "rooms": ["!stage:unknown"],
            "not_rooms": ["!piggyshouse:muppets"],
            "types": ["m.room.message", "muppets.kermit.*"],
            "not_types": ["muppets.misspiggy.*"]
        }
        event = MockEvent(
            sender="@kermit:muppets",  # yup
            type="m.room.message",  # yup
            room_id="!stage:unknown"  # yup
        )
        self.assertTrue(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_combined_event_bad_sender(self):
        definition = {
            "not_senders": ["@misspiggy:muppets"],
            "senders": ["@kermit:muppets"],
            "rooms": ["!stage:unknown"],
            "not_rooms": ["!piggyshouse:muppets"],
            "types": ["m.room.message", "muppets.kermit.*"],
            "not_types": ["muppets.misspiggy.*"]
        }
        event = MockEvent(
            sender="@misspiggy:muppets",  # nope
            type="m.room.message",  # yup
            room_id="!stage:unknown"  # yup
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_combined_event_bad_room(self):
        definition = {
            "not_senders": ["@misspiggy:muppets"],
            "senders": ["@kermit:muppets"],
            "rooms": ["!stage:unknown"],
            "not_rooms": ["!piggyshouse:muppets"],
            "types": ["m.room.message", "muppets.kermit.*"],
            "not_types": ["muppets.misspiggy.*"]
        }
        event = MockEvent(
            sender="@kermit:muppets",  # yup
            type="m.room.message",  # yup
            room_id="!piggyshouse:muppets"  # nope
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    def test_definition_combined_event_bad_type(self):
        definition = {
            "not_senders": ["@misspiggy:muppets"],
            "senders": ["@kermit:muppets"],
            "rooms": ["!stage:unknown"],
            "not_rooms": ["!piggyshouse:muppets"],
            "types": ["m.room.message", "muppets.kermit.*"],
            "not_types": ["muppets.misspiggy.*"]
        }
        event = MockEvent(
            sender="@kermit:muppets",  # yup
            type="muppets.misspiggy.kisses",  # nope
            room_id="!stage:unknown"  # yup
        )
        self.assertFalse(
            self.filtering._passes_definition(definition, event)
        )

    @defer.inlineCallbacks
    def test_add_filter(self):
        user_filter = {
            "room": {
                "state": {
                    "types": ["m.*"]
                }
            }
        }

        filter_id = yield self.filtering.add_user_filter(
            user_localpart=user_localpart,
            user_filter=user_filter,
        )

        self.assertEquals(filter_id, 0)
        self.assertEquals(user_filter,
            (yield self.datastore.get_user_filter(
                user_localpart=user_localpart,
                filter_id=0,
            ))
        )

    @defer.inlineCallbacks
    def test_get_filter(self):
        user_filter = {
            "room": {
                "state": {
                    "types": ["m.*"]
                }
            }
        }

        filter_id = yield self.datastore.add_user_filter(
            user_localpart=user_localpart,
            user_filter=user_filter,
        )

        filter = yield self.filtering.get_user_filter(
            user_localpart=user_localpart,
            filter_id=filter_id,
        )

        self.assertEquals(filter, user_filter)