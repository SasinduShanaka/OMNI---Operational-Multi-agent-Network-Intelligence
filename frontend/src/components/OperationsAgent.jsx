import { useState } from 'react'


// ============================================================
// API CONFIGURATION
// ============================================================

const API_BASE_URL = 'http://127.0.0.1:8000'


// ============================================================
// OPERATIONS AGENT COMPONENT
// ============================================================

function OperationsAgent() {

  // ----------------------------------------------------------
  // User message
  // ----------------------------------------------------------

  const [message, setMessage] = useState('')


  // ----------------------------------------------------------
  // Backend response
  // ----------------------------------------------------------

  const [agentResponse, setAgentResponse] = useState(null)


  // ----------------------------------------------------------
  // Loading state
  // ----------------------------------------------------------

  const [isAsking, setIsAsking] = useState(false)


  // ----------------------------------------------------------
  // Error
  // ----------------------------------------------------------

  const [error, setError] = useState('')


  // ==========================================================
  // ASK OPERATIONS AGENT
  // ==========================================================

  async function handleAskAgent() {

    // Do nothing if input is empty
    if (!message.trim()) {
      return
    }

    setIsAsking(true)
    setError('')
    setAgentResponse(null)

    try {

      // ------------------------------------------------------
      // Send request to FastAPI
      // ------------------------------------------------------

      const response = await fetch(
        `${API_BASE_URL}/ask`,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',
          },

          body: JSON.stringify({
            message: message.trim(),
          }),
        }
      )


      // ------------------------------------------------------
      // Check HTTP response
      // ------------------------------------------------------

      if (!response.ok) {

        throw new Error(
          `Request failed: ${response.status}`
        )

      }


      // ------------------------------------------------------
      // Convert response to JSON
      // ------------------------------------------------------

      const data = await response.json()


      // ------------------------------------------------------
      // Store response
      // ------------------------------------------------------

      setAgentResponse(data)

    } catch (error) {

      console.error(error)

      setError(
        'Could not connect to the Operations Agent. ' +
        'Make sure the FastAPI backend is running.'
      )

    } finally {

      setIsAsking(false)

    }
  }


  // ==========================================================
  // SUGGESTED QUESTIONS
  // ==========================================================

  const suggestedQuestions = [

    'Which materials are low in stock?',

    'How much Black Cotton Fabric do we have?',

    'What is our total inventory?',

    'Do we have enough Black Cotton Fabric for 4000 meters?',

  ]


  // ==========================================================
  // HANDLE SUGGESTED QUESTION
  // ==========================================================

  function handleSuggestedQuestion(question) {

    setMessage(question)

    setError('')

  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="w-full">


      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="mb-5">

        <h2 className="text-2xl font-bold text-white">
          Operations Agent
        </h2>

        <p className="text-slate-400 mt-1">
          Ask the Operations Agent about inventory and
          operational status.
        </p>

      </div>


      {/* ======================================================
          INPUT + BUTTON
      ====================================================== */}

      <div className="flex flex-col md:flex-row gap-3">

        <input
          type="text"
          value={message}
          onChange={(event) => {
            setMessage(event.target.value)
          }}
          onKeyDown={(event) => {

            if (event.key === 'Enter') {
              handleAskAgent()
            }

          }}
          placeholder="Example: How much Black Cotton Fabric do we have?"
          className="
            flex-1
            px-5
            py-4
            rounded-xl
            bg-slate-950/70
            border
            border-white/10
            text-white
            placeholder-slate-500
            outline-none
            focus:border-indigo-400
            transition
          "
        />


        <button
          onClick={handleAskAgent}
          disabled={
            isAsking ||
            !message.trim()
          }
          className="
            px-7
            py-4
            rounded-xl
            bg-indigo-500
            hover:bg-indigo-400
            text-white
            font-semibold
            transition
            disabled:opacity-50
            disabled:cursor-not-allowed
          "
        >

          {isAsking
            ? 'Asking...'
            : 'Ask Agent'
          }

        </button>

      </div>


      {/* ======================================================
          SUGGESTED QUESTIONS
      ====================================================== */}

      <div className="flex flex-wrap gap-2 mt-4">

        {suggestedQuestions.map((question) => (

          <button
            key={question}
            onClick={() => {
              handleSuggestedQuestion(question)
            }}
            className="
              px-4
              py-2
              rounded-lg
              bg-white/5
              border
              border-white/10
              text-sm
              text-slate-300
              hover:bg-white/10
              transition
            "
          >

            {question}

          </button>

        ))}

      </div>


      {/* ======================================================
          ERROR MESSAGE
      ====================================================== */}

      {error && (

        <div
          className="
            mt-5
            p-4
            rounded-xl
            bg-red-500/10
            border
            border-red-400/20
            text-red-300
          "
        >

          {error}

        </div>

      )}


      {/* ======================================================
          AGENT RESPONSE
      ====================================================== */}

      {agentResponse && (

        <div
          className="
            mt-6
            p-6
            rounded-2xl
            bg-slate-950/70
            border
            border-white/10
          "
        >


          {/* ==================================================
              AGENT INFORMATION
          ================================================== */}

          <div
            className="
              grid
              grid-cols-2
              md:grid-cols-4
              gap-5
              mb-6
            "
          >


            {/* AGENT */}

            <div>

              <p className="text-sm text-slate-500">
                Agent
              </p>

              <p className="text-white font-semibold">
                {agentResponse.agent || 'Operations Agent'}
              </p>

            </div>


            {/* INTENT */}

            <div>

              <p className="text-sm text-slate-500">
                Intent
              </p>

              <p className="text-indigo-300 font-semibold">
                {agentResponse.intent || 'N/A'}
              </p>

            </div>


            {/* DELEGATED TO */}

            <div>

              <p className="text-sm text-slate-500">
                Delegated To
              </p>

              <p className="text-indigo-300 font-semibold">
                {agentResponse.delegated_to || 'None'}
              </p>

            </div>


            {/* STATUS */}

            <div>

              <p className="text-sm text-slate-500">
                Status
              </p>

              <p
                className={
                  agentResponse.status === 'success'
                    ? 'text-green-400 font-semibold'
                    : 'text-red-400 font-semibold'
                }
              >
                {agentResponse.status || 'unknown'}
              </p>

            </div>

          </div>


          {/* ==================================================
              AGENT ANSWER
          ================================================== */}

          {agentResponse.answer && (

            <div className="mb-6">

              <p className="text-sm text-slate-500 mb-2">
                Agent Answer
              </p>

              <p
                className="
                  text-xl
                  text-white
                  leading-relaxed
                  whitespace-pre-line
                "
              >

                {agentResponse.answer.replace(
                  /\*\*/g,
                  ''
                )}

              </p>

            </div>

          )}


          {/* ==================================================
              INVENTORY REQUIREMENT
          ================================================== */}

          {agentResponse.result &&
            agentResponse.intent === 'inventory_requirement' && (

            <InventoryRequirementCard
              result={agentResponse.result}
            />

          )}


          {/* ==================================================
              SPECIFIC MATERIAL
          ================================================== */}

          {agentResponse.result &&
            agentResponse.intent === 'material_status' && (

            <MaterialStatusCard
              result={agentResponse.result}
            />

          )}


          {/* ==================================================
              TOTAL STOCK
          ================================================== */}

          {agentResponse.result &&
            agentResponse.intent === 'total_stock' && (

            <TotalStockCard
              result={agentResponse.result}
            />

          )}


          {/* ==================================================
              LOW STOCK
          ================================================== */}

          {agentResponse.results &&
            Array.isArray(agentResponse.results) &&
            agentResponse.results.length > 0 && (

            <LowStockCard
              results={agentResponse.results}
            />

          )}

        </div>

      )}

    </div>

  )
}


// ============================================================
// INVENTORY REQUIREMENT CARD
// ============================================================

function InventoryRequirementCard({ result }) {

  const isShortage =
    result.status === 'SHORTAGE'


  return (

    <div
      className="
        p-5
        rounded-xl
        bg-white/5
        border
        border-white/10
      "
    >

      {/* HEADER */}

      <div className="flex items-center justify-between mb-5">

        <h3 className="text-lg font-semibold text-white">
          Inventory Requirement
        </h3>

        <span
          className={
            isShortage
              ? `
                px-3
                py-1
                rounded-full
                text-xs
                font-semibold
                bg-red-500/10
                text-red-400
              `
              : `
                px-3
                py-1
                rounded-full
                text-xs
                font-semibold
                bg-green-500/10
                text-green-400
              `
          }
        >

          {isShortage
            ? 'SHORTAGE'
            : 'SUFFICIENT'
          }

        </span>

      </div>


      {/* DATA */}

      <div
        className="
          grid
          grid-cols-2
          md:grid-cols-4
          gap-4
        "
      >

        <div>

          <p className="text-sm text-slate-500">
            Material
          </p>

          <p className="text-white font-medium">
            {result.material_name}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Available
          </p>

          <p className="text-white font-medium">
            {result.available_quantity}{' '}
            {result.unit}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Required
          </p>

          <p className="text-white font-medium">
            {result.required_quantity}{' '}
            {result.unit}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Shortage
          </p>

          <p
            className={
              isShortage
                ? 'text-red-400 font-medium'
                : 'text-green-400 font-medium'
            }
          >

            {result.shortage}{' '}
            {result.unit}

          </p>

        </div>

      </div>


      {/* MESSAGE */}

      {result.message && (

        <div
          className={
            isShortage
              ? `
                mt-5
                p-4
                rounded-lg
                bg-red-500/10
                text-red-300
              `
              : `
                mt-5
                p-4
                rounded-lg
                bg-green-500/10
                text-green-300
              `
          }
        >

          {result.message}

        </div>

      )}

    </div>

  )
}


// ============================================================
// MATERIAL STATUS CARD
// ============================================================

function MaterialStatusCard({ result }) {

  const isLowStock =
    result.status === 'LOW_STOCK'


  return (

    <div
      className="
        p-5
        rounded-xl
        bg-white/5
        border
        border-white/10
      "
    >

      <h3 className="text-lg font-semibold text-white mb-5">
        Inventory Details
      </h3>


      <div
        className="
          grid
          grid-cols-2
          md:grid-cols-4
          gap-4
        "
      >

        <div>

          <p className="text-sm text-slate-500">
            Material
          </p>

          <p className="text-white font-medium">
            {result.material_name}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Current Stock
          </p>

          <p className="text-white font-medium">
            {result.current_stock}{' '}
            {result.unit}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Reorder Level
          </p>

          <p className="text-white font-medium">
            {result.reorder_level}{' '}
            {result.unit}
          </p>

        </div>


        <div>

          <p className="text-sm text-slate-500">
            Shortage
          </p>

          <p
            className={
              isLowStock
                ? 'text-red-400 font-medium'
                : 'text-green-400 font-medium'
            }
          >

            {result.shortage}{' '}
            {result.unit}

          </p>

        </div>

      </div>


      {/* RECOMMENDATION */}

      {result.recommendation && (

        <div className="mt-4">

          <p className="text-sm text-slate-500">
            Recommendation
          </p>

          <p className="text-indigo-300 font-medium">
            {result.recommendation}
          </p>

        </div>

      )}

    </div>

  )
}


// ============================================================
// TOTAL STOCK CARD
// ============================================================

function TotalStockCard({ result }) {

  return (

    <div
      className="
        p-5
        rounded-xl
        bg-white/5
        border
        border-white/10
      "
    >

      <h3 className="text-lg font-semibold text-white mb-4">
        Total Inventory
      </h3>


      <div className="flex items-end gap-3">

        <span className="text-4xl font-bold text-white">

          {result.total_stock}

        </span>

        <span className="text-slate-400 mb-1">

          {result.unit}

        </span>

      </div>

    </div>

  )
}


// ============================================================
// LOW STOCK CARD
// ============================================================

function LowStockCard({ results }) {

  return (

    <div className="space-y-3">

      <div className="flex items-center justify-between">

        <h3 className="text-lg font-semibold text-white">
          Low Stock Materials
        </h3>

        <span className="text-red-400 font-semibold">
          {results.length} item
          {results.length !== 1 ? 's' : ''}
        </span>

      </div>


      {results.map((item) => (

        <div
          key={item.material_code}
          className="
            p-4
            rounded-xl
            bg-white/5
            border
            border-white/10
          "
        >


          {/* MATERIAL HEADER */}

          <div className="flex justify-between">

            <div>

              <p className="text-white font-semibold">
                {item.material_name}
              </p>

              <p className="text-sm text-slate-500">
                {item.material_code}
              </p>

            </div>


            <span className="text-red-400 font-semibold">
              LOW STOCK
            </span>

          </div>


          {/* INVENTORY DATA */}

          <div
            className="
              grid
              grid-cols-2
              md:grid-cols-3
              gap-4
              mt-4
              text-sm
            "
          >

            <div>

              <p className="text-slate-500">
                Current Stock
              </p>

              <p className="text-white">
                {item.current_stock}{' '}
                {item.unit}
              </p>

            </div>


            <div>

              <p className="text-slate-500">
                Reorder Level
              </p>

              <p className="text-white">
                {item.reorder_level}{' '}
                {item.unit}
              </p>

            </div>


            <div>

              <p className="text-slate-500">
                Shortage
              </p>

              <p className="text-red-400">
                {item.shortage}{' '}
                {item.unit}
              </p>

            </div>

          </div>


          {/* RECOMMENDATION */}

          {item.recommendation && (

            <p className="mt-4 text-indigo-300">
              {item.recommendation}
            </p>

          )}

        </div>

      ))}

    </div>

  )
}


export default OperationsAgent