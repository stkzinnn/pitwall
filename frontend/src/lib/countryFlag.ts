/**
 * Country name -> flag emoji. Emoji flags are plain Unicode text (built
 * from regional-indicator code points, not images), so there's no
 * copyright concern the way there would be with a flag icon asset.
 *
 * Keyed defensively with a couple of name variants per country (FastF1's
 * `Country` field spelling has varied a bit across seasons/circuits).
 */
const COUNTRY_ISO_CODES: Record<string, string> = {
  Bahrain: 'BH',
  'Saudi Arabia': 'SA',
  Australia: 'AU',
  Japan: 'JP',
  China: 'CN',
  'United States': 'US',
  USA: 'US',
  Italy: 'IT',
  Monaco: 'MC',
  Canada: 'CA',
  Spain: 'ES',
  Austria: 'AT',
  'United Kingdom': 'GB',
  'Great Britain': 'GB',
  England: 'GB',
  Hungary: 'HU',
  Belgium: 'BE',
  Netherlands: 'NL',
  Azerbaijan: 'AZ',
  Singapore: 'SG',
  Mexico: 'MX',
  Brazil: 'BR',
  Qatar: 'QA',
  'United Arab Emirates': 'AE',
  UAE: 'AE',
  'Abu Dhabi': 'AE',
  Germany: 'DE',
  France: 'FR',
  Portugal: 'PT',
  Russia: 'RU',
  Turkey: 'TR',
  'South Korea': 'KR',
  India: 'IN',
  Malaysia: 'MY',
  Vietnam: 'VN',
}

function flagEmojiFromIso(isoCode: string): string {
  const codePoints = [...isoCode.toUpperCase()].map(
    (char) => 0x1f1e6 + (char.charCodeAt(0) - 'A'.charCodeAt(0)),
  )
  return String.fromCodePoint(...codePoints)
}

/** Returns a flag emoji for a known country name, or null if unrecognized
 * (callers should just omit the flag rather than guess). */
export function getCountryFlag(country: string | null): string | null {
  if (!country) return null
  const isoCode = COUNTRY_ISO_CODES[country]
  return isoCode ? flagEmojiFromIso(isoCode) : null
}
