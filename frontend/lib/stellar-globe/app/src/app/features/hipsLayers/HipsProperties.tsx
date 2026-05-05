type Card = {
  key: string
  value: string
}

export type HipsProperties = {
  cards: Card[]
}

export function parseHipsProperties(input: string): HipsProperties {
  const lines = input.split('\n')
  const cards: Card[] = []

  lines.forEach(line => {
    // コメント行を無視
    if (!line.startsWith('#') && line.trim() !== '') {
      const [key, value] = line.split('=', 2).map(part => part.trim())
      if (key && value) {
        cards.push({ key, value })
      }
    }
  })

  return {
    cards,
  }
}
