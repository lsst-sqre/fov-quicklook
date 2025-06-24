import { useEffect, useState } from "react"
import { CopyTemplate, copyTemplateSlice } from "../../store/features/copyTemplateSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"


export function ConfigPage() {
  const [selected, setSelected] = useState<string>()

  return (
    <div>
      <h1>Config</h1>
      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <CopyTemplateList setSelected={setSelected} selected={selected} />
        <CopyTemplateEditor selected={selected} setSelected={setSelected} />
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


function CopyTemplateEditor({ selected, setSelected }: { selected?: string, setSelected: (name: string) => void }) {
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('')
  const [isUrl, setIsUrl] = useState(false)
  const templates = useAppSelector(state => state.copyTemplate.templates)
  const dispatch = useAppDispatch()

  const selectedTemplate = templates.find(t => t.name === selected)
  const isEditable = selectedTemplate?.isLocal === true

  useEffect(() => {
    if (selectedTemplate) {
      setName(selectedTemplate.name)
      setTemplate(selectedTemplate.template)
      setIsUrl(selectedTemplate.is_url)
    }
  }, [selectedTemplate])

  const handleAdd = () => {
    const newName = prompt('Enter template name:')
    if (newName && newName.trim()) {
      const newTemplate: CopyTemplate = {
        name: newName.trim(),
        template: '',
        is_url: false,
        isLocal: true
      }
      dispatch(copyTemplateSlice.actions.updateTemplate(newTemplate))
      setSelected(newName.trim())
    }
  }

  return (
    <div>
      <dl>
        <dt>
          Read-only:
        </dt>
        <dd>
          <input type="checkbox" checked={!selectedTemplate?.isLocal} readOnly />
        </dd>
        <dt>Name:</dt>
        <dd>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!isEditable}
          />
        </dd>
        <dt>Template:</dt>
        <dd>
          <textarea
            cols={80}
            rows={8}
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            disabled={!isEditable}
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
            disabled={!isEditable}
          />
        </dd>
      </dl>
      <button onClick={handleAdd}>
        New
      </button>
      <button
        onClick={() => {

          const updatedTemplate: CopyTemplate = { name, template, is_url: isUrl, isLocal: true }
          dispatch(copyTemplateSlice.actions.updateTemplate(updatedTemplate))
          setSelected(name)
        }}
        disabled={!isEditable}
      >
        Save
      </button>
      <button
        onClick={() => {
          const idx = templates.findIndex(t => t.name === name)
          if (idx >= 0) {
            dispatch(copyTemplateSlice.actions.removeTemplate(templates[idx]))
          }
        }}
        disabled={!isEditable}
      >
        Delete
      </button>
      <button onClick={() => {
        dispatch(copyTemplateSlice.actions.resetToDefault())
      }}>Reset to Default</button>
    </div>
  )
}
