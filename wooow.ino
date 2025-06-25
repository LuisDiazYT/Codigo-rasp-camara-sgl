// --- Pines de Control de Motores ---
// Estos pines controlan la dirección de los motores.
const int IN1 = 4; // Motor Izquierdo - Adelante
const int IN2 = 5; // Motor Izquierdo - Atrás
const int IN3 = 6; // Motor Derecho - Adelante
const int IN4 = 7; // Motor Derecho - Atrás

// NOTA: No se declaran ENA ni ENB ya que no se usarán (o están cableados directamente a HIGH/VCC).

// --- Umbrales de Error para el Giro ---
// Estos valores definen cuándo el robot debe girar y qué tan fuerte.
// Son CRÍTICOS y deben ajustarse mediante prueba y error.
const int UMBRAL_GIRO_SUAVE = 20;  // Error abs (ej. |error|) mayor que esto, para giro suave
const int UMBRAL_GIRO_FUERTE = 80; // Error abs (ej. |error|) mayor que esto, para giro fuerte

// Añadir un retardo global para transiciones de motor (para estabilidad)
const int MOTOR_TRANSITION_DELAY = 15; // Ajusta este valor (en milisegundos).

// --- Variable para almacenar el error recibido ---
int currentError = 0;

void setup() {
  Serial.begin(9600); // Asegúrate de que la velocidad coincida con la de la Raspberry Pi
  
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Si tu driver L298N tiene pines ENA/ENB y no los controlas con PWM,
  // pero necesitas activarlos para que los motores funcionen,
  // conéctalos a un pin digital del Arduino y ponlo en HIGH aquí, o directamente a 5V.
  // Ejemplo si tuvieras un pin ENA/ENB conectado al pin 8:
  // pinMode(8, OUTPUT);
  // digitalWrite(8, HIGH); // Activar ENA/ENB para velocidad máxima
  
  detener(); // Asegurarse de que los motores estén apagados al inicio
  Serial.println("Arduino listo para recibir comandos (Sin control de velocidad PWM).");
}

void loop() {
  if (Serial.available()) {
    String incomingData = Serial.readStringUntil('\n'); // Lee la cadena completa hasta el salto de línea

    // Comprobamos si la cadena comienza con 'E' (indicando que es un valor de error)
    if (incomingData.startsWith("E")) {
      currentError = incomingData.substring(1).toInt(); // Extrae el número después de 'E'

      // --- Lógica de Control de Giro (Basada en Umbrales de Error) ---
      if (currentError < -UMBRAL_GIRO_FUERTE) { // Línea muy a la izquierda (error negativo grande)
        giroFuerteIzquierda();
        Serial.print("Error: "); Serial.print(currentError); Serial.println(", Giro Fuerte Izquierda");
      } else if (currentError < -UMBRAL_GIRO_SUAVE) { // Línea un poco a la izquierda
        giroSuaveIzquierda();
        Serial.print("Error: "); Serial.print(currentError); Serial.println(", Giro Suave Izquierda");
      } else if (currentError > UMBRAL_GIRO_FUERTE) { // Línea muy a la derecha (error positivo grande)
        giroFuerteDerecha();
        Serial.print("Error: "); Serial.print(currentError); Serial.println(", Giro Fuerte Derecha");
      } else if (currentError > UMBRAL_GIRO_SUAVE) { // Línea un poco a la derecha
        giroSuaveDerecha();
        Serial.print("Error: "); Serial.print(currentError); Serial.println(", Giro Suave Derecha");
      } else { // Línea centrada
        avanzarRecto();
        Serial.print("Error: "); Serial.print(currentError); Serial.println(", Avanzando Recto");
      }
    } else if (incomingData.startsWith("S")) { // Comando 'S' para detener (cuando no se encuentra línea)
        detener();
        Serial.println("Detenido por comando 'S'");
    } else {
      Serial.print("Comando desconocido o formato incorrecto: ");
      Serial.println(incomingData);
      detener(); // Detener si hay un comando desconocido o mal formato
    }
    
    delay(MOTOR_TRANSITION_DELAY); // Pequeño retardo para la estabilidad
  }
}

// --- Funciones de Control de Movimiento ---

void avanzarRecto() {
  digitalWrite(IN1, HIGH); // Motor Izquierdo Adelante
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); // Motor Derecho Adelante
  digitalWrite(IN4, LOW);
}

void giroFuerteIzquierda() {
  digitalWrite(IN1, LOW);  // Motor Izquierdo Atrás (o LOW/LOW para detenerlo y que pivote)
  digitalWrite(IN2, HIGH); // Para giro sobre el eje: Motor Izquierdo Atrás
                           // Para giro más suave: digitalWrite(IN1, LOW); digitalWrite(IN2, LOW); (detener izq)
  digitalWrite(IN3, HIGH); // Motor Derecho Adelante
  digitalWrite(IN4, LOW);
}

void giroSuaveIzquierda() {
  digitalWrite(IN1, LOW);  // Motor Izquierdo Detenido
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); // Motor Derecho Adelante
  digitalWrite(IN4, LOW);
}

void giroFuerteDerecha() {
  digitalWrite(IN1, HIGH); // Motor Izquierdo Adelante
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);  // Motor Derecho Atrás (o LOW/LOW para detenerlo y que pivote)
  digitalWrite(IN4, HIGH); // Para giro sobre el eje: Motor Derecho Atrás
                           // Para giro más suave: digitalWrite(IN3, LOW); digitalWrite(IN4, LOW); (detener der)
}

void giroSuaveDerecha() {
  digitalWrite(IN1, HIGH); // Motor Izquierdo Adelante
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);  // Motor Derecho Detenido
  digitalWrite(IN4, LOW);
}

void detener() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}
