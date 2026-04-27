import type { ConsolePayload } from '../types/console'

import { AskNewPage } from './AskNewPage'

type AskPageProps = {
  data: ConsolePayload | null
}

function AskPage({ data }: AskPageProps) {
  return <AskNewPage data={data} />
}

export default AskPage
