import type { ConsolePayload } from '../types/console'

import { GenerateNewPage } from './GenerateNewPage'

type GeneratePageProps = {
  data: ConsolePayload | null
  templateName: string
}

function GeneratePage({ data, templateName }: GeneratePageProps) {
  return <GenerateNewPage data={data} templateName={templateName} />
}

export default GeneratePage
