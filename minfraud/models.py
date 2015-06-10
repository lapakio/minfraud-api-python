"""
minfraud.models
~~~~~~~~~~~~~~~

This module contains models for the minFraud response object.

"""
from collections import namedtuple
from functools import update_wrapper

import geoip2.models
import geoip2.records


# Using a factory decorator rather than a metaclass as supporting
# metaclasses on Python 2 and 3 is more painful (although we could use
# six, I suppose). Using a closure rather than a class-based decorator as
# class based decorators don't work right with `update_wrapper`,
# causing help(class) to not work correctly.
def _inflate_to_namedtuple(orig_cls):
    keys = sorted(orig_cls._fields.keys())
    fields = orig_cls._fields
    name = orig_cls.__name__
    orig_cls.__name__ += 'Super'
    nt = namedtuple(name, keys)
    nt.__name__ = name + 'NamedTuple'
    nt.__new__.__defaults__ = (None, ) * len(keys)
    new_cls = type(name, (nt, orig_cls),
                   {'__slots__': (),
                    '__doc__': orig_cls.__doc__})
    update_wrapper(_inflate_to_namedtuple, new_cls)
    orig_new = new_cls.__new__

    # wipe out original namedtuple field docs as they aren't useful
    # for attr in fields:
    #     getattr(cls, attr).__func__.__doc__ = None

    def new(cls, *args, **kwargs):
        if (args and kwargs) or len(args) > 1:
            raise ValueError('Only provide a single (dict) positional argument'
                             ' or use keyword arguments. Do not use both.')
        if args:
            values = args[0] if args[0] else {}

            for field, default in fields.items():
                if callable(default):
                    kwargs[field] = default(values.get(field))
                else:
                    kwargs[field] = values.get(field, default)

        return orig_new(cls, **kwargs)

    new_cls.__new__ = staticmethod(new)
    return new_cls


def _create_warnings(warnings):
    if not warnings:
        return ()
    return tuple([Warning(x) for x in warnings])


class GeoIP2Location(geoip2.records.Location):
    """
    Location information for the IP address

    In addition to the attributes provided by ``geoip2.records.Location``,
    this class provides:

    .. attribute:: local_time

      The date and time of the transaction in the time
      zone associated with the IP address. The value is formatted according to
      `RFC 3339 <http://tools.ietf.org/html/rfc3339>`_. For instance, the
      local time in Boston might be returned as 2015-04-27T19:17:24-04:00.

      :type: str | None


    Parent:

    """
    __doc__ += geoip2.records.Location.__doc__
    _valid_attributes = geoip2.records.Location._valid_attributes.union(
        set(['local_time']))


class GeoIP2Country(geoip2.records.Country):
    """
    Country information for the IP address

    In addition to the attributes provided by ``geoip2.records.Country``,
    this class provides:

    .. attribute:: is_high_risk

      This is true if the IP country is high risk.

      :type: bool | None


    Parent:

    """
    __doc__ += geoip2.records.Country.__doc__
    _valid_attributes = geoip2.records.Country._valid_attributes.union(
        set(['is_high_risk']))


class IPAddress(geoip2.models.Insights):
    """
    Model for minFraud and GeoIP2 data about the IP address

    .. attribute:: risk

      This field contains the risk associated with the IP address. The value
      ranges from 0.01 to 99. A higher score indicates a higher risk.

      :type: float | None

    .. attribute:: city

      City object for the requested IP address.

      :type: :py:class:`geoip2.records.City`

    .. attribute:: continent

      Continent object for the requested IP address.

      :type: :py:class:`geoip2.records.Continent`

    .. attribute:: country

      Country object for the requested IP address. This record represents the
      country where MaxMind believes the IP is located.

      :type: :py:class:`GeoIP2Country`

    .. attribute:: location

      Location object for the requested IP address.

      :type: :py:class:`GeoIP2Location`

    .. attribute:: maxmind

      Information related to your MaxMind account.

      :type: :py:class:`geoip2.records.MaxMind`

    .. attribute:: registered_country

      The registered country object for the requested IP address. This record
      represents the country where the ISP has registered a given IP block in
      and may differ from the user's country.

      :type: :py:class:`geoip2.records.Country`

    .. attribute:: represented_country

      Object for the country represented by the users of the IP address
      when that country is different than the country in ``country``. For
      instance, the country represented by an overseas military base.

      :type: :py:class:`geoip2.records.RepresentedCountry`

    .. attribute:: subdivisions

      Object (tuple) representing the subdivisions of the country to which
      the location of the requested IP address belongs.

      :type: :py:class:`geoip2.records.Subdivisions`

    .. attribute:: traits

      Object with the traits of the requested IP address.

    """

    def __init__(self, ip_address):
        if ip_address is None:
            ip_address = {}
        locales = ip_address.get('_locales')
        if '_locales' in ip_address:
            del ip_address['_locales']
        super(IPAddress, self).__init__(ip_address, locales=locales)
        self.country = GeoIP2Country(locales, **ip_address.get('country', {}))
        self.location = GeoIP2Location(**ip_address.get('location', {}))
        self.risk = ip_address.get('risk', None)
        self._finalized = True

    # Unfortunately the GeoIP2 models are not immutable, only the records. This
    # corrects that for minFraud
    def __setattr__(self, name, value):
        if hasattr(self, '_finalized') and self._finalized:
            raise AttributeError("can't set attribute")
        super(IPAddress, self).__setattr__(name, value)


@_inflate_to_namedtuple
class Issuer(object):
    """
    Information about the credit card issuer.

    .. attribute:: name

      The name of the bank which issued the credit card.

      :type: str | None

    .. attribute:: matches_provided_name

      This property is ``True`` if the name matches
      the name provided in the request for the card issuer. It is ``False`` if
      the name does not match. The property is ``None`` if either no name or
      no issuer ID number (IIN) was provided in the request or if MaxMind does
      not have a name associated with the IIN.

      :type: bool

    .. attribute:: phone_number

      The phone number of the bank which issued the credit
      card. In some cases the phone number we return may be out of date.

      :type: str

    .. attribute:: matches_provided_phone_number

      This property is ``True`` if the phone
      number matches the number provided in the request for the card issuer. It
      is ``False`` if the number does not match. It is ``None`` if either no
      phone number or no issuer ID number (IIN) was provided in the request or
      if MaxMind does not have a phone number associated with the IIN.

      :type: bool

    """
    __slots__ = ()
    _fields = {
        'name': None,
        'matches_provided_name': None,
        'phone_number': None,
        'matches_provided_phone_number': None
    }


@_inflate_to_namedtuple
class CreditCard(object):
    """
    Information about the credit card based on the issuer ID number

    .. attribute:: country

      This property contains an `ISO 3166-1 alpha-2 country
      code <http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>`_ representing
      the country that the card was issued in.

      :type: str | None

    .. attribute:: is_issued_in_billing_address_country

      This property is true if the
      country of the billing address matches the country that the credit card
      was issued in.

      :type: bool | None

    .. attribute:: is_prepaid

      This property is ``True`` if the card is a prepaid card.

      :type: bool | None

    .. attribute:: issuer

      An object containing information about the credit card issuer.

      :type: Issuer

    """
    __slots__ = ()
    _fields = {
        'issuer': Issuer,
        'country': None,
        'is_issued_in_billing_address_country': None,
        'is_prepaid': None
    }


@_inflate_to_namedtuple
class BillingAddress(object):
    """
    Information about the billing address

    .. attribute:: distance_to_ip_location

      The distance in kilometers from the
      address to the IP location.

      :type: int | None

    .. attribute:: is_in_ip_country

      This property is ``True`` if the address is in the
      IP country. The property is ``False`` when the address is not in the IP
      country. If the address could not be parsed or was not provided or if the
      IP address could not be geolocated, the property will be ``None``.

      :type: bool | None

    .. attribute:: is_postal_in_city

      This property is ``True`` if the postal code
      provided with the address is in the city for the address. The property is
      ``False`` when the postal code is not in the city. If the address could
      not be parsed or was not provided, the property will be ``None``.

      :type: bool | None

    .. attribute:: latitude

      The latitude associated with the address.

      :type: float | None

    .. attribute:: longitude

      The longitude associated with the address.

      :type: float | None

    """
    __slots__ = ()
    _fields = {
        'is_postal_in_city': None,
        'latitude': None,
        'longitude': None,
        'distance_to_ip_location': None,
        'is_in_ip_country': None
    }


@_inflate_to_namedtuple
class ShippingAddress(object):
    """
    Information about the shipping address

    .. attribute:: distance_to_ip_location

      The distance in kilometers from the
      address to the IP location.

      :type: int | None

    .. attribute:: is_in_ip_country

      This property is ``True`` if the address is in the
      IP country. The property is ``False`` when the address is not in the IP
      country. If the address could not be parsed or was not provided or if the
      IP address could not be geolocated, the property will be ``None``.

      :type: bool | None

    .. attribute:: is_postal_in_city

      This property is ``True`` if the postal code
      provided with the address is in the city for the address. The property is
      ``False`` when the postal code is not in the city. If the address could
      not be parsed or was not provided, the property will be ``None``.

      :type: bool | None

    .. attribute:: latitude

      The latitude associated with the address.

      :type: float | None

    .. attribute:: longitude

      The longitude associated with the address.

      :type: float | None

    .. attribute:: is_high_risk

      This property is ``True`` if the shipping address is in
      the IP country. The property is ``false`` when the address is not in the
      IP country. If the shipping address could not be parsed or was not
      provided or the IP address could not be geolocated, then the property is
      ``None``.

      :type: bool | None

    .. attribute:: distance_to_billing_address

      The distance in kilometers from the
      shipping address to billing address.

      :type: int | None

    """
    __slots__ = ()
    _fields = {
        'is_postal_in_city': None,
        'latitude': None,
        'longitude': None,
        'distance_to_ip_location': None,
        'is_in_ip_country': None,
        'is_high_risk': None,
        'distance_to_billing_address': None
    }


@_inflate_to_namedtuple
class Warning(object):
    """
    Warning from the web service

    .. attribute:: code

      This value is a machine-readable code identifying the
      warning. See the `web service documentation
      <http://dev.maxmind.com/minfraud-score-and-insights-api-documentation/#Warning_Object>`_
      for the current list of of warning codes.

      :type: str

    .. attribute:: warning

      This property provides a human-readable explanation of the
      warning. The description may change at any time and should not be matched
      against.

      :type: str

    .. attribute:: input

      This is a tuple of keys representing the path to the input that
      the warning is associated with. For instance, if the warning was about the
      billing city, the tuple would be ``("billing", "city")``. The key is used
      for an object and the index number for an array.

      :type: tuple[str|int]

    """
    __slots__ = ()
    _fields = {
        'code': None,
        'warning': None,
        'input': lambda x: tuple(x) if x else ()
    }


@_inflate_to_namedtuple
class Insights(object):
    """
    Model for Insights response

    .. attribute:: id

      This is a UUID that identifies the minFraud request. Please use
      this ID in bug reports or support requests to MaxMind so that we can
      easily identify a particular request.

      :type: str

    .. attribute:: credits_remaining

      The approximate number of service credits remaining
      on your account.

      :type: int

    .. attribute:: warnings

      This tuple contains :class:`.Warning` objects detailing
      issues with the request that was sent such as invalid or unknown inputs.
      It is highly recommended that you check this array for issues when
      integrating the web service.

      :type: tuple[Warning]

    .. attribute:: risk_score

      This property contains the risk score, from 0.01 to 99. A
      higher score indicates a higher risk of fraud. For example, a score of 20
      indicates a 20% chance that a transaction is fraudulent. We never return a
      risk score of 0, since all transactions have the possibility of being
      fraudulent. Likewise we never return a risk score of 100.

      :type: float

    .. attribute:: credit_card

      A :class:`.CreditCard` object containing minFraud data
      about the credit card used in the transaction.

      :type: CreditCard

    .. attribute:: ip_address

      A :class:`.IPAddress` object containing GeoIP2 and
      minFraud Insights information about the IP address.

      :type: IPAddress

    .. attribute:: billing_address

      A :class:`.BillingAddress` object containing minFraud
      data related to the billing address used in the transaction.

      :type: BillingAddress

    .. attribute:: shipping_address

      A :class:`.ShippingAddress` object containing
      minFraud data related to the shipping address used in the transaction.
    """
    __slots__ = ()
    _fields = {
        'id': None,
        'risk_score': None,
        'warnings': _create_warnings,
        'credits_remaining': None,
        'ip_address': IPAddress,
        'credit_card': CreditCard,
        'shipping_address': ShippingAddress,
        'billing_address': BillingAddress
    }


@_inflate_to_namedtuple
class Score(object):
    """
    Model for Score response

    .. attribute:: id

      This is a UUID that identifies the minFraud request. Please use
      this ID in bug reports or support requests to MaxMind so that we can
      easily identify a particular request.

      :type: str

    .. attribute:: credits_remaining

      The approximate number of service credits remaining
      on your account.

      :type: int

    .. attribute:: warnings

      This tuple contains :class:`.Warning` objects detailing
      issues with the request that was sent such as invalid or unknown inputs.
      It is highly recommended that you check this array for issues when
      integrating the web service.

      :type: tuple[Warning]

    .. attribute:: risk_score

      This property contains the risk score, from 0.01 to 99. A
      higher score indicates a higher risk of fraud. For example, a score of 20
      indicates a 20% chance that a transaction is fraudulent. We never return a
      risk score of 0, since all transactions have the possibility of being
      fraudulent. Likewise we never return a risk score of 100.

      :type: float

    """
    __slots__ = ()
    _fields = {
        'id': None,
        'risk_score': None,
        'warnings': _create_warnings,
        'credits_remaining': None,
    }
