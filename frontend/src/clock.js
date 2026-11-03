export function formatToday(date) {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(date);
}

export function websiteClock(response) {
  const date = Date.parse(response.headers.get('date'));
  const age = Number(response.headers.get('age') || 0);
  if (!response.ok || !Number.isFinite(date) || !Number.isFinite(age) || age < 0) throw new Error('Website server time unavailable');
  return date + age * 1000;
}
