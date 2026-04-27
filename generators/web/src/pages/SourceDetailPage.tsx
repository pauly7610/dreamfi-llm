import type { ConsolePayload } from '../types/console'

import { SourceNewPage } from './SourceNewPage'

type SourceDetailPageProps = {
  data: ConsolePayload | null
  sourceId: string | null
}

function SourceDetailPage({ data, sourceId }: SourceDetailPageProps) {
  return <SourceNewPage data={data} sourceId={sourceId} />
}

export default SourceDetailPage
