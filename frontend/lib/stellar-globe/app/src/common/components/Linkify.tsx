import { memo } from "react"

type LinkifyProps = {
  text: string
}

export const Linkify = memo(({ text }: LinkifyProps) => {
  const linkifyText = (text: string) => {
    const urlRegex = /(\bhttps?:\/\/[-A-Z0-9+&@#/%?=~_|!:,.;]*[-A-Z0-9+&@#/%=~_|])/gi
    return text.split(urlRegex).map((part, index) =>
      urlRegex.test(part) ? (
        <a key={index} href={part} target="_blank" rel="noreferrer">
          {part}
        </a>
      ) : (
        part
      )
    )
  }

  return <div>{linkifyText(text)}</div>
})
