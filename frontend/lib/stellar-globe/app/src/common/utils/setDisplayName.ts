import { Component } from "react"

export function setDisplayName(components: Record<string, { displayName?: string }>) {
  for (const name of Object.keys(components)) {
    components[name].displayName = name
  }
}