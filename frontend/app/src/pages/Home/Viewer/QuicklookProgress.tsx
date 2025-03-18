import { Progress } from "../../../components/Progress"
import { RoundedFrame } from "../../../components/RoundedFrame"
import { QuicklookStatus } from "../../../store/api/openapi"

export function QuicklookProgress({ status }: { status: QuicklookStatus} ) {
  return (
    <div>
      {/* {status && status.generating_progress && (
        Object.entries(status.generating_progress).map(([pod, progress]) => (
          <div key={pod}>
            <div>{pod}</div>
            <RoundedFrame>
              <Progress count={progress.download.count} total={progress.download.total} />
              <Progress count={progress.preprocess.count} total={progress.preprocess.total} />
              <Progress count={progress.maketile.count} total={progress.maketile.total} />
            </RoundedFrame>
          </div>
        ))
      )} */}
    </div>
  )
}
