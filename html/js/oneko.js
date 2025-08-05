// oneko.js: https://github.com/adryd325/oneko.js

(function oneko() {
  const isReducedMotion =
    window.matchMedia(`(prefers-reduced-motion: reduce)`) === true ||
    window.matchMedia(`(prefers-reduced-motion: reduce)`).matches === true;

  if (isReducedMotion) return;

  const nekoEl = document.createElement("div");

  let nekoPosX = 70; 
  let nekoPosY = 100;

  let mousePosX = 70; 
  let mousePosY = 100;

  let frameCount = 0;
  let idleTime = 0;
  let idleAnimation = null;
  let idleAnimationFrame = 0;

  const nekoSpeed = 10;
  const spriteSets = {
    idle: [[-3, -3]],
    alert: [[-7, -3]],
    scratchSelf: [
      [-5, 0],
      [-6, 0],
      [-7, 0],
    ],
    scratchWallN: [
      [0, 0],
      [0, -1],
    ],
    scratchWallS: [
      [-7, -1],
      [-6, -2],
    ],
    scratchWallE: [
      [-2, -2],
      [-2, -3],
    ],
    scratchWallW: [
      [-4, 0],
      [-4, -1],
    ],
    tired: [[-3, -2]],
    sleeping: [
      [-2, 0],
      [-2, -1],
    ],
    N: [
      [-1, -2],
      [-1, -3],
    ],
    NE: [
      [0, -2],
      [0, -3],
    ],
    E: [
      [-3, 0],
      [-3, -1],
    ],
    SE: [
      [-5, -1],
      [-5, -2],
    ],
    S: [
      [-6, -3],
      [-7, -2],
    ],
    SW: [
      [-5, -3],
      [-6, -1],
    ],
    W: [
      [-4, -2],
      [-4, -3],
    ],
    NW: [
      [-1, 0],
      [-1, -1],
    ],
  };

  function resize(num) {
    const scaleFactor = 0.2;
    const scale = num * scaleFactor - scaleFactor + 1;

    nekoEl.style.transform = `scale(${scale})`;
    treats.forEach(treat => {
      treat.style.transform = `scale(${scale})`;
    });
  }

  function init() {
    nekoEl.id = "oneko";
    nekoEl.ariaHidden = true;
    nekoEl.style.width = "32px";
    nekoEl.style.height = "32px";
    nekoEl.style.position = "fixed";
    nekoEl.style.pointerEvents = "none";
    nekoEl.style.imageRendering = "pixelated";
    nekoEl.style.left = `${nekoPosX - 16}px`;
    nekoEl.style.top = `${nekoPosY - 16}px`;
    nekoEl.style.zIndex = 2147483647;

    let nekoFile = "./assets/img/oneko.gif"
    const curScript = document.currentScript
    if (curScript && curScript.dataset.cat) {
      nekoFile = curScript.dataset.cat
    }
    nekoEl.style.backgroundImage = `url(${nekoFile})`;

    document.body.appendChild(nekoEl);

    // Create size input container
    const sizeContainer = document.createElement("div");
    sizeContainer.style.position = "absolute"; // Changed from fixed to absolute
    sizeContainer.style.top = "10px";
    sizeContainer.style.left = "10px";
    sizeContainer.style.zIndex = 2147483646;
    sizeContainer.style.background = "rgba(0, 0, 0, 0.7)";
    sizeContainer.style.padding = "5px 10px";
    sizeContainer.style.borderRadius = "5px";
    sizeContainer.style.display = "flex";
    sizeContainer.style.alignItems = "center";
    sizeContainer.style.gap = "10px";

    // Create label
    const label = document.createElement("span");
    label.textContent = "Krokmou Scale";
    label.style.color = "#fff";
    label.style.fontFamily = "monospace";
    label.style.fontSize = "14px";

    // Create size input
    const sizeInput = document.createElement("input");
    sizeInput.type = "number";
    sizeInput.min = "1";
    sizeInput.max = "10";
    sizeInput.value = "1";
    sizeInput.style.width = "50px";
    sizeInput.style.background = "transparent";
    sizeInput.style.border = "none";
    sizeInput.style.color = "#fff";
    sizeInput.style.fontFamily = "monospace";
    sizeInput.style.fontSize = "14px";
    sizeInput.addEventListener("input", (e) => {
        resize(Number(e.target.value));
    });

    sizeContainer.appendChild(label);
    sizeContainer.appendChild(sizeInput);
    document.body.appendChild(sizeContainer);

    document.addEventListener("mousemove", function (event) {
        mousePosX = event.clientX;
        mousePosY = event.clientY;
    });

    // treats functionality
    initTreats();

    window.requestAnimationFrame(onAnimationFrame);
  }

  let lastFrameTimestamp;

  function onAnimationFrame(timestamp) {
    
    if (!nekoEl.isConnected) {
      return;
    }
    if (!lastFrameTimestamp) {
      lastFrameTimestamp = timestamp;
    }
    if (timestamp - lastFrameTimestamp > 100) {
      lastFrameTimestamp = timestamp
      frame()
    }
    window.requestAnimationFrame(onAnimationFrame);
  }

  function setSprite(name, frame) {
    const sprite = spriteSets[name][frame % spriteSets[name].length];
    nekoEl.style.backgroundPosition = `${sprite[0] * 32}px ${sprite[1] * 32}px`;
  }

  function resetIdleAnimation() {
    idleAnimation = null;
    idleAnimationFrame = 0;
  }

  function idle() {
    idleTime += 1;

    
    if (
      idleTime > 10 &&
      Math.floor(Math.random() * 50) == 0 && 
      idleAnimation == null
    ) {
      let avalibleIdleAnimations = ["sleeping", "scratchSelf"];
      if (nekoPosX < 32) {
        avalibleIdleAnimations.push("scratchWallW");
      }
      if (nekoPosY < 32) {
        avalibleIdleAnimations.push("scratchWallN");
      }
      if (nekoPosX > window.innerWidth - 32) {
        avalibleIdleAnimations.push("scratchWallE");
      }
      if (nekoPosY > window.innerHeight - 32) {
        avalibleIdleAnimations.push("scratchWallS");
      }
      idleAnimation =
        avalibleIdleAnimations[
          Math.floor(Math.random() * avalibleIdleAnimations.length)
        ];
    }

    switch (idleAnimation) {
      case "sleeping":
        if (idleAnimationFrame < 8) {
          setSprite("tired", 0);
          break;
        }
        setSprite("sleeping", Math.floor(idleAnimationFrame / 4));
        if (idleAnimationFrame > 192) {
          resetIdleAnimation();
        }
        break;
      case "scratchWallN":
      case "scratchWallS":
      case "scratchWallE":
      case "scratchWallW":
      case "scratchSelf":
        setSprite(idleAnimation, idleAnimationFrame);
        if (idleAnimationFrame > 9) {
          resetIdleAnimation();
        }
        break;
      default:
        setSprite("idle", 0);
        return;
    }
    idleAnimationFrame += 1;
  }

  function frame() {
    frameCount += 1;
    let toTreat = false;
    let posX;
    let posY;


    if (treats.length > 0) {
      toTreat = true;
      const treat = treats[0];
      posX = parseInt(treat.style.left);
      posY = parseInt(treat.style.top);
    } else {
      posX = mousePosX;
      posY = mousePosY;
    }

    const diffX = nekoPosX - posX;
    const diffY = nekoPosY - posY;
    const distance = Math.sqrt(diffX ** 2 + diffY ** 2);

    if (distance < nekoSpeed || (toTreat ? distance < 12 : distance < 48)) {
      if (treats.length > 0) {
        const treat = treats[0];
        treat.remove();
        treats.splice(0, 1);
      }
      idle();
      return;
    }

    idleAnimation = null;
    idleAnimationFrame = 0;

    if (idleTime > 1) {
      setSprite("alert", 0);
    
      idleTime = Math.min(idleTime, 7);
      idleTime -= 1;
      return;
    }

    let direction;
    direction = diffY / distance > 0.5 ? "N" : "";
    direction += diffY / distance < -0.5 ? "S" : "";
    direction += diffX / distance > 0.5 ? "W" : "";
    direction += diffX / distance < -0.5 ? "E" : "";
    setSprite(direction, frameCount);

    nekoPosX -= (diffX / distance) * nekoSpeed;
    nekoPosY -= (diffY / distance) * nekoSpeed;

    nekoPosX = Math.min(Math.max(16, nekoPosX), window.innerWidth - 16);
    nekoPosY = Math.min(Math.max(16, nekoPosY), window.innerHeight - 16);

    nekoEl.style.left = `${nekoPosX - 16}px`;
    nekoEl.style.top = `${nekoPosY - 16}px`;
  }

  // Treat implementation inspired by flleeppyy (https://github.com/flleeppyy)
  let treats = []; 
  let treatsEnabled = false; // disable treats by default

  function initTreats() {
    
    const toggleContainer = document.createElement("div");
    toggleContainer.style.position = "absolute"; 
    toggleContainer.style.top = "45px"; 
    toggleContainer.style.left = "10px"; 
    toggleContainer.style.zIndex = 2147483646;
    toggleContainer.style.background = "rgba(0, 0, 0, 0.7)";
    toggleContainer.style.padding = "5px 10px";
    toggleContainer.style.borderRadius = "5px";
    toggleContainer.style.display = "flex";
    toggleContainer.style.alignItems = "center";
    toggleContainer.style.gap = "10px";

    
    const label = document.createElement("label");
    label.textContent = "Enable Treats";
    label.style.color = "#fff";
    label.style.fontFamily = "monospace";
    label.style.fontSize = "14px";

    
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = treatsEnabled;
    checkbox.style.cursor = "pointer";

    checkbox.addEventListener("change", () => {
      treatsEnabled = checkbox.checked;
    });

    toggleContainer.appendChild(label);
    toggleContainer.appendChild(checkbox);
    document.body.appendChild(toggleContainer);

    // click event listener treats
    document.addEventListener('click', (event) => {
      if (treatsEnabled) {
        placeTreat(event.clientX, event.clientY);
      }
    });
  
    // T key binding as alternative
    document.addEventListener("keyup", event => {
      if (event.key === "t" && treatsEnabled) {
        placeTreat(mousePosX, mousePosY);
      }
    });
  }
  
  function placeTreat(x, y) {
    const treat = document.createElement("div");
    treat.className = "oneko-treat";
    treat.style.left = `${x}px`;
    treat.style.top = `${y}px`;
    treat.style.backgroundImage = `url(./assets/img/treat.png)`;
    document.body.appendChild(treat);
    treats.push(treat);
  }
  init();
})();
