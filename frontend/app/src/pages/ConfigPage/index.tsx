import { useEffect, useState } from "react"
import { copyTemplateSlice } from "../../store/features/copyTemplateSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"


export function ConfigPage() {
  const [selected, setSelected] = useState<string>()

  return (
    <div>
      <h1>Config</h1>
      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <CopyTemplateList setSelected={setSelected} selected={selected} />
        <CopyTemplateEditor selected={selected} />
      </div>
    </div>
  )
}


function CopyTemplateList({ setSelected, selected }: {
  setSelected: (name: string) => void,
  selected?: string,
}) {
  const templates = useAppSelector(state => state.copyTemplate.templates)

  return (
    <div>
      <select size={2} onChange={(e) => setSelected(e.target.value)} value={selected}
        style={{ width: '200px', height: '200px' }}
      >
        {templates.map(t => <option key={t.name}>{t.name}</option>)}
      </select>
    </div>
  )
}


function CopyTemplateEditor({ selected }: { selected?: string }) {
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('')
  const [isUrl, setIsUrl] = useState(false)
  const templates = useAppSelector(state => state.copyTemplate.templates)
  const dispatch = useAppDispatch()

  useEffect(() => {
    const selectedTemplate = templates.find(t => t.name === selected)
    if (selectedTemplate) {
      setName(selectedTemplate.name)
      setTemplate(selectedTemplate.template)
      setIsUrl(selectedTemplate.isUrl)
    }
  }, [selected, templates])

  return (
    <div>

      <dl>
        <dt>Name:</dt>
        <dd>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </dd>
        <dt>Template:</dt>
        <dd>
          <textarea
            cols={80}
            rows={8}
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          />
        </dd>
        <dt>is URL:</dt>
        <dd>
          <input
            type="checkbox"
            checked={isUrl}
            onChange={(e) => {
              setIsUrl(e.target.checked)
            }}
          />
        </dd>
      </dl>
      <button onClick={() => {
        const updatedTemplate = { name, template, isUrl }
        dispatch(copyTemplateSlice.actions.updateTemplate(updatedTemplate))
      }}>Save</button>
      <button onClick={() => {
        const idx = templates.findIndex(t => t.name === name)
        if (idx >= 0) {
          dispatch(copyTemplateSlice.actions.removeTemplate(templates[idx]))
        }
      }}>Delete</button>
      <button onClick={() => {
        dispatch(copyTemplateSlice.actions.resetToDefault())
      }}>Reset to Default</button>
    </div>
  )
}
