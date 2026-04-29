import type { ConsolePayload } from '../types/console'

import { InboxNewPage } from './InboxNewPage'

type ReviewPageProps = {
  data: ConsolePayload | null
  onDataChanged?: () => void
}

function ReviewPage({ data, onDataChanged }: ReviewPageProps) {
  return <InboxNewPage data={data} onDataChanged={onDataChanged} />
}

export default ReviewPage
