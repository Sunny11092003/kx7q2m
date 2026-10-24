const BASE = import.meta.env.VITE_API_URL || ''

export async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}