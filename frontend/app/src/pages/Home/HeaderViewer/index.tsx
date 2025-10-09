import { useMemo } from "react"
import { CcdMetadata, useGetFitsHeaderQuery } from "../../../store/api/openapi"
import { useFocusedAmp, useFocusedCcd } from "../hooks"


export function HeaderViewer() {
  const focusedCcd = useFocusedCcd()
  return (
    <div style={{ height: '300px', overflowY: 'auto', boxShadow: '0 0 4px white inset' }}>
      {/* {focusedCcd && <HeaderViewerOfCcd ccd={focusedCcd} />} */}
    </div>
  )
}

// TODO: revive
// function HeaderViewerOfCcd({ ccd }: { ccd: CcdMetadata }) {
//   const { ccd_name, visit } = ccd
//   const { data } = useGetFitsHeaderQuery({ ccdName: ccd_name, id: `${visit.id}` })
//   const focusedAmp = useFocusedAmp()
//   const headerNumber = useMemo(() => focusedAmp?.amp_id ?? 0, [focusedAmp])

//   return (
//     <div>
//       {headerNumber}
//       {data && (
//         <table style={{ tableLayout: 'fixed', }}>
//           <thead>
//           </thead>
//           <tbody>
//             {data[headerNumber].slice(10).map(([keyword, type, value, comment], i) => (
//               <tr key={i}>
//                 <td>{keyword}</td>
//                 <td>{type}</td>
//                 <td>{value}</td>
//                 <td>{comment}</td>
//               </tr>
//             ))}
//           </tbody>
//         </table>
//       )}
//     </div >
//   )
// }
