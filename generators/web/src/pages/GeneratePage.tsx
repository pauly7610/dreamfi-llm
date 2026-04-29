import type { ConsolePayload } from '../types/console'

import { GenerateNewPage } from './GenerateNewPage'

type GeneratePageProps = {
  data: ConsolePayload | null
  onDataChanged?: () => void
  templateName: string
}

function GeneratePage({ data, onDataChanged, templateName }: GeneratePageProps) {
  return <GenerateNewPage data={data} onDataChanged={onDataChanged} templateName={templateName} />
}

export default GeneratePage
